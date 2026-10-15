import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, models, transaction
from django.utils import timezone

from auditoria.models import BitacoraAuditoria
from calificaciones.documentos import registrar_versiones, version_documento
from calificaciones.models import (CalificacionTributaria, FactorTributario, Instrumento,
                                   calcular_factores_desde_montos, errores_factores, leer_factor)
from cargas.documentos import guardar_resultado_carga

TAMANO_MAXIMO_BYTES = settings.CSV_TAMANO_MAXIMO_MB * 1024 * 1024  # HU-06: 10 MB (configurable)
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


def _entero(texto, columna):
    try:
        return int(texto)
    except ValueError:
        raise ValueError(f"columna {columna}: '{texto}' no es un número entero")


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

    # ---------- Lectura y validación del archivo ----------
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

    # ---------- Procesamiento ----------
    def _validar_fila(self, fila, instrumentos, existentes, es_montos):
        """Valida una fila en memoria e indica columna y motivo de cada error (HU-06 criterio 3)."""
        ejercicio, mercado, nemo, fecha, secuencia, dividendo, tipo_soc, valor_hist = [v.strip() for v in fila[:8]]

        instrumento = instrumentos.get(nemo)
        if instrumento is None:
            raise ValueError(f"columna Instrumento: '{nemo}' no existe")
        if instrumento.emisor.mercado != mercado.upper():
            raise ValueError(f"columna Mercado: '{mercado}' no corresponde al del instrumento {nemo}")

        ejercicio = _entero(ejercicio, "Ejercicio")
        secuencia = _entero(secuencia, "Secuencia")
        dividendo = _entero(dividendo, "N.º dividendo")
        if not 1900 <= ejercicio <= 2100:
            raise ValueError(f"columna Ejercicio: {ejercicio} no es válido")
        if not 10001 <= secuencia <= SECUENCIA_MAXIMA:
            raise ValueError("columna Secuencia: debe ser mayor a 10.000")
        if dividendo < 0:
            raise ValueError("columna N.º dividendo: no puede ser negativo")
        tipo_soc = tipo_soc.upper()
        if tipo_soc not in ("", "A", "C"):
            raise ValueError("columna Tipo sociedad: debe ser A o C")
        try:
            fecha_pago = datetime.strptime(fecha, "%d-%m-%Y").date()
        except ValueError:
            raise ValueError(f"columna Fecha: '{fecha}' debe tener el formato DD-MM-AAAA")
        try:
            valor_historico = _decimal(valor_hist)
        except (ValueError, InvalidOperation):
            raise ValueError(f"columna Valor histórico: '{valor_hist}' no es un número válido")

        llave = (instrumento.id, ejercicio, secuencia)
        existente = existentes.get(llave)
        if existente and existente.verificar_periodo_cerrado():
            raise ValueError("la calificación pertenece a un período cerrado y no se puede modificar")

        valores = {}
        for columna, texto in zip(COLUMNAS, fila[8:]):
            if es_montos:
                try:
                    valores[columna] = _decimal(texto)
                except (ValueError, InvalidOperation):
                    raise ValueError(f"columna {columna}: '{texto}' no es un monto válido")
            else:
                valores[columna] = leer_factor(texto, columna)  # HU-07: hasta 8 decimales

        factores = calcular_factores_desde_montos(valores) if es_montos else valores
        errores = errores_factores(factores)  # HU-05: indica qué factor falla
        if errores:
            raise ValueError("; ".join(errores))

        campos = {"fecha_pago": fecha_pago, "numero_dividendo": dividendo,
                  "tipo_sociedad": tipo_soc, "valor_historico": valor_historico}
        return llave, instrumento, existente, campos, valores, factores

    def procesar_lote(self, ip=None):
        """Upsert masivo por llave [Supuesto]: corredora + instrumento + ejercicio comercial + secuencia de evento.
        MySQL guarda los datos; MongoDB, el detalle de la carga y el historial de versiones."""
        corredora = self.cargado_por.corredora
        if corredora is None:
            raise ValidationError("Tu usuario no está asociado a una corredora, por lo que no puede cargar archivos.")

        filas = self._leer_filas()
        previsualizacion = filas[:11]  # encabezado + 10 filas
        if not (self.validar_tamano_maximo() and self.validar_formato(filas)):
            errores = [f"El archivo supera el tamaño permitido ({settings.CSV_TAMANO_MAXIMO_MB} MB) "
                       f"o no tiene las {COLUMNAS_ESPERADAS} columnas requeridas."]
            self.estado_carga = self.EstadoCarga.CON_ERRORES
            self.save()
            guardar_resultado_carga(self, {"filas": max(len(filas) - 1, 0), "validas": 0,
                                           "rechazadas": max(len(filas) - 1, 0)}, errores, previsualizacion)
            return errores

        datos = filas[1:]
        es_montos = self.formato_tipo == self.TipoCarga.MONTOS
        Forma = CalificacionTributaria.FormaActualizacion
        origen = Forma.CARGA_MONTOS if es_montos else Forma.CARGA_FACTORES

        # 1. Precarga en memoria (2 consultas a MySQL)
        nemos = {fila[2].strip() for fila in datos}
        ejercicios = {int(fila[0]) for fila in datos if fila[0].strip().isdigit()}
        instrumentos = {i.codigo_nemotecnico: i for i in
                        Instrumento.objects.select_related("emisor").filter(codigo_nemotecnico__in=nemos)}
        existentes = {(c.instrumento_id, c.ejercicio_comercial, c.secuencia_evento): c for c in
                      CalificacionTributaria.objects.filter(corredora=corredora,
                                                            instrumento__in=instrumentos.values(),
                                                            ejercicio_comercial__in=ejercicios)}

        # 2. Validación en memoria (sin consultas)
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

        # 3. Escritura en bloque en MySQL: todo o nada para las filas válidas
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

                # 4. Factores: se reemplazan completos (composición 1 → 30), en bloques para cuidar la memoria
                FactorTributario.objects.filter(calificacion__in=actualizadas).delete()
                lote = []
                for llave, _, _, _, valores, factores in validas:
                    calificacion = por_llave[llave]
                    for columna in COLUMNAS:
                        lote.append(FactorTributario(
                            calificacion=calificacion, columna=columna,
                            monto_financiero=valores[columna] if es_montos else Decimal("0"),
                            factor_calculado=factores[columna]))
                    if len(lote) >= LOTE_BD:
                        FactorTributario.objects.bulk_create(lote, batch_size=LOTE_BD)
                        lote = []
                if lote:
                    FactorTributario.objects.bulk_create(lote, batch_size=LOTE_BD)

                # 5. Bitácora en MySQL, en la misma transacción
                BitacoraAuditoria.registrar_evento(
                    self.cargado_por, BitacoraAuditoria.TipoAccion.CARGA_MASIVA, ip, "ArchivoCSV", self.pk,
                    forma=origen, valor_nuevo={"creadas": len(nuevas), "actualizadas": len(actualizadas),
                                               "rechazadas": len(errores)})

                # 6. Historial en MongoDB: solo si MySQL confirma la transacción
                versiones = [version_documento(por_llave[llave], factores, origen, self.cargado_por.email,
                                               f"Carga {self.nombre_archivo}", ahora)
                             for llave, _, _, _, _, factores in validas]
                transaction.on_commit(lambda: registrar_versiones(versiones))
        except DatabaseError:
            errores.append("Error al guardar en la base de datos: no se guardó ninguna fila. Intente nuevamente.")
            validas, nuevas, actualizadas = [], [], []

        self.filas_validas = len(validas)
        self.filas_rechazadas = self.total_filas - len(validas)
        self.estado_carga = self.EstadoCarga.CON_ERRORES if errores else self.EstadoCarga.CARGADA
        self.save()

        # 7. Detalle de la carga en MongoDB
        guardar_resultado_carga(self, {"filas": self.total_filas, "validas": self.filas_validas,
                                       "rechazadas": self.filas_rechazadas, "creadas": len(nuevas),
                                       "actualizadas": len(actualizadas)}, errores, previsualizacion)
        return errores

    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_estado_carga_display()})"