import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

TAMANO_MAXIMO_BYTES = settings.CSV_TAMANO_MAXIMO_MB * 1024 * 1024  # [Supuesto] 5 MB
COLUMNAS_ESPERADAS = 38 # 8 campos fijos + 30 columnas (8 a 37). Segun HDU

def _decimal(valor):
    """ Convierte texto a Decimal con 8 decimales.
    Acepta punto o coma como separador decimal y vacio (= 0).
    Rechaza valores con separador de miles."""

    texto = valor.strip() or "0"
    if "," in texto and "." in texto:
        raise ValueError(f"el valor '{valor}' tiene separador de miles; ingreselo sin separador (ej. 1000,05)")
    return Decimal(texto.replace(",", ".")).quantize(Decimal("0.00000001"))
    

class ArchivoCSV(models.Model):
    class TipoCarga(models.TextChoices):
        MONTOS = "MONTOS", "Por montos (DJ 1948)"
        FACTORES = "FACTORES", "Por factores"

    class EstadoCarga(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        VALIDADA = "VALIDADA", "Validada"
        CARGADA = "CARGADA", "Cargada"
        CON_ERRORES = "CON_ERRORES", "Con errores"

    cargado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="archivos_cargados")
    archivo = models.FileField(upload_to="cargas/%Y/%m")


    # Atributos

    nombre_archivo = models.CharField(max_length=255, blank=True)
    tamano_bytes = models.PositiveIntegerField(default=0)
    formato_tipo = models.CharField(max_length=10, choices=TipoCarga.choices)
    total_filas = models.PositiveIntegerField(default=0)
    filas_validas = models.PositiveIntegerField(default=0)
    filas_rechazadas = models.PositiveIntegerField(default=0)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estado_carga = models.CharField(max_length=15, choices=EstadoCarga.choices, default=EstadoCarga.PENDIENTE)

    def save(self, *args, **kwargs):
        if self.archivo and not self.nombre_archivo:
            self.nombre_archivo = self.archivo.name
            self.tamano_bytes = self.archivo.size
        super().save(*args, **kwargs)

    def _leer_filas(self):
        """ Lee el CSV aceptando UTF-8 o Latin-1 y separador ; o,"""
        with self.archivo.open("rb") as f:
            datos = f.read()
        try:
            texto = datos.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = datos.decode("latin-1")
        try:
            dialecto = csv.Sniffer().sniff(texto[:2048], delimiters=";,")
        except csv.Error:
            dialecto = csv.excel
        return [fila for fila in csv.reader(io.StringIO(texto), dialecto) if any(fila)]

    def validar_tamano_maximo(self):
        return self.tamano_bytes <= TAMANO_MAXIMO_BYTES

    def validar_formato(self):
        """ Extension .csv y todas las filas con 18 columnas """
        if not self.nombre_archivo.lower().endswith(".csv"): # .endswith comprueba si un texto termina con cierto valor, Devuelve True o False
            return False
        filas = self._leer_filas()
        if len(filas) < 2: # encabezado + al menos una fila
            return False
        self.total_filas = len(filas) - 1
        return all(len(fila) == COLUMNAS_ESPERADAS for fila in filas)

    def previsualizar_datos(self, cantidad=10):
        filas = self._leer_filas()
        return {"encabezado": filas[0], "filas": filas[1:cantidad + 1]}

    def procesar_lote(self):
        """ Upsert por llave [Supuesto]: corredora + instrumento + ejercicio comercial + secuencia de evento."""
        from calificaciones.models import CalificacionTributaria, FactorTributario, Instrumento

        corredora = self.cargado_por.corredora
        if corredora is None:
            raise ValidationError("Tu usuario no esta asociado a una corredora, por lo que no puede cargar archivos.")

        if not (self.validar_tamano_maximo() and self.validar_formato()):
            self.estado_carga = self.EstadoCarga.CON_ERRORES
            self.save()
            return ["El archivo no cumple el tamaño maximo o el formato de 38 columnas."]

        es_montos = self.formato_tipo == self.TipoCarga.MONTOS
        Forma = CalificacionTributaria.FormaActualizacion
        origen = Forma.CARGA_MONTOS if es_montos else Forma.CARGA_FACTORES
        campo_valor = "monto_financiero" if es_montos else "factor_calculado"

        errores, validas = [], 0
        for numero_fila, fila in enumerate(self._leer_filas()[1:], start=2):
            try:
                with transaction.atomic(): # si la fila falla, se deshace solo esa fila
                    ejercicio, mercado, nemo, fecha, secuencia, dividendo, tipo_soc, valor_hist = fila[:8]
                    valores = [_decimal(v) for v in fila[8:]]

                    instrumento = Instrumento.objects.select_related("emisor").get(
                        codigo_nemotecnico=nemo.strip()
                    )
                    if instrumento.emisor.mercado != mercado.strip().upper():
                        raise ValueError(f"el mercado {mercado} no coindice con el del instrumento ")

                    llave = {
                        "corredora": corredora,
                        "instrumento": instrumento,
                        "ejercicio_comercial": int(ejercicio),
                        "secuencia_evento": int(secuencia),
                    }
                    calificacion = CalificacionTributaria.objects.filter(**llave).first()
                    if calificacion and calificacion.verificar_periodo_cerrado():
                        raise ValueError("la calificación pertenece a un periodo cerrado")
                    if calificacion is None:
                        calificacion = CalificacionTributaria(**llave)

                    calificacion.fecha_pago = datetime.strptime(fecha.strip(), "%d-%m-%Y").date()
                    calificacion.numero_dividendo = int(dividendo)
                    calificacion.tipo_sociedad = tipo_soc.strip().upper()
                    calificacion.valor_historico = _decimal(valor_hist)
                    calificacion.origen_dato = origen
                    calificacion.archivo_origen = self
                    calificacion.registrado_por = self.cargado_por
                    calificacion.activo = True
                    calificacion.full_clean()
                    calificacion.save()

                    for columna, valor in zip(range(8, 38), valores):
                        FactorTributario.objects.update_or_create(
                            calificacion=calificacion, columna=columna, defaults={campo_valor:valor}
                        )

                    if es_montos:
                        calificacion.calcular_factores()
                    if not calificacion.validar_consistencia():
                        raise ValueError("los factores no cumplen las reglas: cada uno debe estar entre 0 y 1, "
                 "y la suma de las columnas 8 a 19 no puede superar 1")
                validas += 1
            except (ValueError, InvalidOperation, ValidationError, Instrumento.DoesNotExist) as error:
                errores.append(f"Fila {numero_fila}: {error}")

        self.filas_validas = validas
        self.filas_rechazadas = len(errores)
        self.estado_carga = self.EstadoCarga.CON_ERRORES if errores else self.EstadoCarga.CARGADA
        self.save()
        return errores

    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_estado_carga_display()})"