import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, models, transaction
from django.utils import timezone

from auditoria.models import BitacoraAuditoria
from calificaciones.models import (CalificacionTributaria, FactorTributario, Instrumento,
                                   calcular_factores_desde_montos, factores_validos)

TAMANO_MAXIMO_BYTES = settings.CSV_TAMANO_MAXIMO_MB * 1024 * 1024  # [Supuesto] 5 MB
COLUMNAS_ESPERADAS = 38       # 8 campos fijos + 30 columnas (8 a 37), según HDU
COLUMNAS = range(8, 38)
LOTE_BD = 1000                # registros por consulta en operaciones masivas
VALOR_MAXIMO = Decimal("1000000000000")  # límite del campo decimal (12 dígitos enteros)
SECUENCIA_MAXIMA = 4_294_967_295         # límite de PositiveIntegerField en MySQL
CAMPOS_ACTUALIZABLES = ["fecha_pago", "numero_dividendo", "tipo_sociedad", "valor_historico", "origen_dato",
                        "archivo_origen", "registrado_por", "activo", "fecha_ultima_modificacion"]


def _decimal(valor):
    """Convierte '0,5', '0.5' o vacío (= 0) a Decimal con 8 decimales. Rechaza separador de miles."""
    texto = valor.strip() or "0"
    if "," in texto and "." in texto:
        raise ValueError(f"el valor '{valor}' tiene separador de miles; ingréselo sin separador (ej. 1000,50)")
    numero = Decimal(texto.replace(",", ".")).quantize(Decimal("0.00000001"))
    if abs(numero) >= VALOR_MAXIMO:
        raise ValueError(f"el valor '{valor}' es demasiado grande")
    return numero


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
    archivo = models.FileField(upload_to="cargas/%Y/%m/")

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

    # Lectura y validación del archivo 
    def _leer_filas(self):
        """Lee el CSV aceptando UTF-8 o Latin-1 y separador ; o ,"""
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

    def validar_formato(self, filas=None):
        """Extensión .csv y todas las filas con 38 columnas."""
        if not self.nombre_archivo.lower().endswith(".csv"):
            return False
        filas = filas if filas is not None else self._leer_filas()
        if len(filas) < 2:  # encabezado + al menos una fila
            return False
        self.total_filas = len(filas) - 1
        return all(len(fila) == COLUMNAS_ESPERADAS for fila in filas)

    def previsualizar_datos(self, cantidad=10):
        filas = self._leer_filas()
        return {"encabezado": filas[0], "filas": filas[1:cantidad + 1]}

    # Procesamiento 
    def _validar_fila(self, fila, instrumentos, existentes, es_montos):
        """Valida una fila en memoria. Devuelve sus datos listos para guardar o lanza ValueError."""
        ejercicio, mercado, nemo, fecha, secuencia, dividendo, tipo_soc, valor_hist = [v.strip() for v in fila[:8]]

        instrumento = instrumentos.get(nemo)
        if instrumento is None:
            raise ValueError(f"el instrumento {nemo} no existe")
        if instrumento.emisor.mercado != mercado.upper():
            raise ValueError(f"el mercado {mercado} no corresponde al del instrumento {nemo}")

        ejercicio, secuencia, dividendo = int(ejercicio), int(secuencia), int(dividendo)
        if not 1900 <= ejercicio <= 2100:
            raise ValueError(f"el ejercicio {ejercicio} no es válido")
        if not 10001 <= secuencia <= SECUENCIA_MAXIMA:
            raise ValueError("la secuencia de evento debe ser mayor a 10.000")
        if dividendo < 0:
            raise ValueError("el número de dividendo no puede ser negativo")
        tipo_soc = tipo_soc.upper()
        if tipo_soc not in ("", "A", "C"):
            raise ValueError("el tipo de sociedad debe ser A o C")

        llave = (instrumento.id, ejercicio, secuencia)
        existente = existentes.get(llave)
        if existente and existente.verificar_periodo_cerrado():
            raise ValueError("la calificación pertenece a un período cerrado y no se puede modificar")

        valores = {columna: _decimal(v) for columna, v in zip(COLUMNAS, fila[8:])}
        factores = calcular_factores_desde_montos(valores) if es_montos else valores
        if not factores_validos(factores):
            raise ValueError("los factores no cumplen las reglas: cada uno debe estar entre 0 y 1, "
                             "y la suma de las columnas 8 a 19 no puede superar 1")

        campos = {
            "fecha_pago": datetime.strptime(fecha, "%d-%m-%Y").date(),
            "numero_dividendo": dividendo,
            "tipo_sociedad": tipo_soc,
            "valor_historico": _decimal(valor_hist),
        }
        return llave, instrumento, existente, campos, valores, factores

    def procesar_lote(self, ip=None):
        """Upsert masivo por llave [Supuesto]: corredora + instrumento + ejercicio comercial + secuencia de evento."""
        corredora = self.cargado_por.corredora
        if corredora is None:
            raise ValidationError("Tu usuario no está asociado a una corredora, por lo que no puede cargar archivos.")

        filas = self._leer_filas()
        if not (self.validar_tamano_maximo() and self.validar_formato(filas)):
            self.estado_carga = self.EstadoCarga.CON_ERRORES
            self.save()
            return ["El archivo supera el tamaño permitido o no tiene las 38 columnas requeridas."]

        datos = filas[1:]
        es_montos = self.formato_tipo == self.TipoCarga.MONTOS
        Forma = CalificacionTributaria.FormaActualizacion
        origen = Forma.CARGA_MONTOS if es_montos else Forma.CARGA_FACTORES

        # Precarga en memoria (2 consultas)
        nemos = {fila[2].strip() for fila in datos}
        ejercicios = {int(fila[0]) for fila in datos if fila[0].strip().isdigit()}
        instrumentos = {i.codigo_nemotecnico: i for i in
                        Instrumento.objects.select_related("emisor").filter(codigo_nemotecnico__in=nemos)}
        existentes = {(c.instrumento_id, c.ejercicio_comercial, c.secuencia_evento): c for c in
                      CalificacionTributaria.objects.filter(corredora=corredora,
                                                            instrumento__in=instrumentos.values(),
                                                            ejercicio_comercial__in=ejercicios)}

        # Validación en memoria (sin consultas)
        errores, validas, llaves_vistas = [], [], set()
        for numero_fila, fila in enumerate(datos, start=2):
            try:
                registro = self._validar_fila(fila, instrumentos, existentes, es_montos)
                if registro[0] in llaves_vistas:
                    raise ValueError("está repetida en el archivo (misma llave que una fila anterior)")
            except (ValueError, InvalidOperation, ValidationError) as error:
                mensaje = error.messages[0] if isinstance(error, ValidationError) else error
                errores.append(f"Fila {numero_fila}: {mensaje}")
                continue
            llaves_vistas.add(registro[0])
            validas.append(registro)

        # Escritura en bloque: todo o nada para las filas válidas
        ahora = timezone.now()
        nuevas, actualizadas = [], []
        try:
            with transaction.atomic():
                for llave, instrumento, existente, campos, _, _ in validas:
                    calificacion = existente or CalificacionTributaria(
                        corredora=corredora, instrumento=instrumento,
                        ejercicio_comercial=llave[1], secuencia_evento=llave[2])
                    for campo, valor in campos.items():
                        setattr(calificacion, campo, valor)
                    calificacion.origen_dato = origen
                    calificacion.archivo_origen = self
                    calificacion.registrado_por = self.cargado_por
                    calificacion.activo = True
                    calificacion.fecha_ultima_modificacion = ahora
                    (actualizadas if existente else nuevas).append(calificacion)

                CalificacionTributaria.objects.bulk_create(nuevas, batch_size=LOTE_BD)
                CalificacionTributaria.objects.bulk_update(actualizadas, CAMPOS_ACTUALIZABLES, batch_size=LOTE_BD)

                # MySQL no devuelve los id creados con bulk_create: se releen por la llave (1 consulta)
                por_llave = {(c.instrumento_id, c.ejercicio_comercial, c.secuencia_evento): c for c in
                             CalificacionTributaria.objects.filter(corredora=corredora, archivo_origen=self)}

                # Factores: se reemplazan completos (composición 1 → 30)
                FactorTributario.objects.filter(calificacion__in=actualizadas).delete()
                FactorTributario.objects.bulk_create([
                    FactorTributario(calificacion=por_llave[llave], columna=columna,
                                     monto_financiero=valores[columna] if es_montos else Decimal("0"),
                                     factor_calculado=factores[columna])
                    for llave, _, _, _, valores, factores in validas
                    for columna in COLUMNAS
                ], batch_size=LOTE_BD)

                #  Un evento de bitácora por archivo
                BitacoraAuditoria.registrar_evento(
                    self.cargado_por, BitacoraAuditoria.TipoAccion.CARGA_MASIVA, ip, "ArchivoCSV", self.pk,
                    forma=origen, valor_nuevo={"creadas": len(nuevas), "actualizadas": len(actualizadas),
                                               "rechazadas": len(errores)})
        except DatabaseError:
            errores.append("Error al guardar en la base de datos: no se guardó ninguna fila. Intente nuevamente.")
            validas = []

        self.filas_validas = len(validas)
        self.filas_rechazadas = self.total_filas - len(validas)
        self.estado_carga = self.EstadoCarga.CON_ERRORES if errores else self.EstadoCarga.CARGADA
        self.save()
        return errores

    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_estado_carga_display()})"