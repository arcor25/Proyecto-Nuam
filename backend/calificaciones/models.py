from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from usuarios.models import Corredora

OCHO_DECIMALES = Decimal("0.00000001")
COLUMNAS_SUMA = range(settings.FACTOR_SUMA_DESDE, settings.FACTOR_SUMA_HASTA + 1)  # [Supuesto] 8 a 19 (HU-27)


# ---------- Reglas de cálculo y validación (reutilizadas por cargas y rectificaciones) ----------

def calcular_factores_desde_montos(montos):
    """HU-04. Recibe {columna: monto} y devuelve {columna: factor} con 8 decimales.
    Factor columna N = monto N / suma de montos de las columnas configuradas (8 a 19)."""
    suma = sum((monto for columna, monto in montos.items() if columna in COLUMNAS_SUMA), Decimal("0"))
    if suma == 0:
        raise ValidationError(f"la suma de montos de las columnas {COLUMNAS_SUMA.start} a "
                              f"{COLUMNAS_SUMA.stop - 1} no puede ser cero")
    return {columna: (monto / suma).quantize(OCHO_DECIMALES, rounding=ROUND_HALF_UP)
            for columna, monto in montos.items()}


def leer_factor(texto, columna):
    """HU-05 y HU-07. Convierte un factor ingresado: número con un entero y hasta 8 decimales."""
    limpio = str(texto).strip() or "0"
    if "," in limpio and "." in limpio:
        raise ValidationError(f"el factor {columna} tiene separador de miles")
    try:
        valor = Decimal(limpio.replace(",", "."))
    except InvalidOperation:
        raise ValidationError(f"el factor {columna} ('{texto}') no es un número válido")
    if valor.as_tuple().exponent < -8:
        raise ValidationError(f"el factor {columna} ('{texto}') tiene más de 8 decimales")
    return valor.quantize(OCHO_DECIMALES)


def errores_factores(factores):
    """HU-05 criterio 3. Un mensaje por cada regla incumplida, indicando el factor.
    Lista vacía = factores válidos."""
    errores = [f"el factor {columna} ({factor}) debe estar entre 0 y 1"
               for columna, factor in sorted(factores.items())
               if not Decimal("0") <= factor <= Decimal("1")]
    suma = sum((factor for columna, factor in factores.items() if columna in COLUMNAS_SUMA), Decimal("0"))
    if suma > 1:
        errores.append(f"la suma de los factores {COLUMNAS_SUMA.start} a {COLUMNAS_SUMA.stop - 1} "
                       f"es {suma} y no puede superar 1")
    return errores


def factores_validos(factores):
    return not errores_factores(factores)


# ---------- Modelos ----------

class Emisor(models.Model):
    class Mercado(models.TextChoices):
        ACN = "ACN", "Acciones"
        CFI = "CFI", "Cuotas de fondos de inversión"
        FM = "FM", "Fondos mutuos"

    rut_emisor = models.CharField(max_length=12, unique=True)
    razon_social = models.CharField(max_length=150)
    mercado = models.CharField(max_length=3, choices=Mercado.choices)
    activo = models.BooleanField(default=True)

    def validar_rut(self):
        """Valida el dígito verificador (módulo 11). Formato: 12345678-9"""
        try:
            cuerpo, dv = self.rut_emisor.replace(".", "").upper().split("-")
            suma, factor = 0, 2
            for digito in reversed(cuerpo):
                suma += int(digito) * factor
                factor = 2 if factor == 7 else factor + 1
            resultado = 11 - (suma % 11)
            dv_esperado = {11: "0", 10: "K"}.get(resultado, str(resultado))
            return dv == dv_esperado
        except ValueError:
            return False

    def clean(self):
        """HU-16: no se guarda un emisor con dígito verificador incorrecto."""
        if not self.validar_rut():
            raise ValidationError({"rut_emisor": "El RUT del emisor no es válido: revise el dígito verificador."})

    def activar(self):
        self.activo = True
        self.save()

    def desactivar(self):
        self.activo = False
        self.save()

    def __str__(self):
        return self.razon_social


class Instrumento(models.Model):
    codigo_nemotecnico = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    esta_inscrito = models.BooleanField(default=True)
    emisor = models.ForeignKey(Emisor, on_delete=models.PROTECT, related_name="instrumentos")

    def validar_nemotecnico(self):
        codigo = self.codigo_nemotecnico.strip()
        return 0 < len(codigo) <= 50

    def obtener_detalle(self):
        return f"{self.codigo_nemotecnico} - {self.descripcion} ({self.emisor})"

    def inscribir(self):
        self.esta_inscrito = True
        self.save()

    def desinscribir(self):
        self.esta_inscrito = False
        self.save()

    def __str__(self):
        return self.codigo_nemotecnico


class CalificacionTributaria(models.Model):
    class FormaActualizacion(models.TextChoices):
        INGRESO_MANUAL = "INGRESO_MANUAL", "Ingreso manual"
        CARGA_MONTOS = "CARGA_MONTOS", "Carga por montos"
        CARGA_FACTORES = "CARGA_FACTORES", "Carga por factores"
        BOLSA = "BOLSA", "Bolsa"

    class EstadoPeriodo(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        CERRADO = "CERRADO", "Cerrado"

    class TipoSociedad(models.TextChoices):
        ABIERTA = "A", "Abierta"
        CERRADA = "C", "Cerrada"

    # Relaciones
    corredora = models.ForeignKey(Corredora, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="calificaciones")  # 0..1: null = calificación de Bolsa
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="calificaciones_registradas")
    instrumento = models.ForeignKey(Instrumento, on_delete=models.PROTECT, related_name="calificaciones")
    archivo_origen = models.ForeignKey("cargas.ArchivoCSV", on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="calificaciones_generadas")  # 0..1

    # Atributos del diagrama
    secuencia_evento = models.PositiveIntegerField(validators=[MinValueValidator(10001)])
    fecha_pago = models.DateField()
    ejercicio_comercial = models.PositiveSmallIntegerField()
    valor_historico = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    descripcion = models.CharField(max_length=255, blank=True)
    is_fut = models.BooleanField(default=False)
    factor_actualizacion = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    origen_dato = models.CharField(max_length=20, choices=FormaActualizacion.choices,
                                   default=FormaActualizacion.INGRESO_MANUAL)
    estado_periodo = models.CharField(max_length=10, choices=EstadoPeriodo.choices, default=EstadoPeriodo.ABIERTO)
    activo = models.BooleanField(default=True)
    fecha_ultima_modificacion = models.DateTimeField(auto_now=True)
    numero_dividendo = models.PositiveIntegerField(default=0)
    tipo_sociedad = models.CharField(max_length=1, choices=TipoSociedad.choices, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["corredora", "instrumento", "ejercicio_comercial", "secuencia_evento"],
                name="llave_calificacion",  # [Supuesto] llave del upsert
            ),
        ]

    def calcular_factores(self):
        factores = list(self.factores.all())
        nuevos = calcular_factores_desde_montos({f.columna: f.monto_financiero for f in factores})
        for f in factores:
            f.factor_calculado = nuevos[f.columna]
        FactorTributario.objects.bulk_update(factores, ["factor_calculado"])

    def errores_consistencia(self):
        """Mensajes de los factores que no cumplen las reglas (vacío = consistente)."""
        return errores_factores({f.columna: f.factor_calculado for f in self.factores.all()})

    def validar_consistencia(self):
        return not self.errores_consistencia()

    def aplicar_borrado_logico(self):
        self.activo = False
        self.save()

    def verificar_periodo_cerrado(self):
        return self.estado_periodo == self.EstadoPeriodo.CERRADO

    def __str__(self):
        return f"{self.instrumento} | {self.ejercicio_comercial} | sec. {self.secuencia_evento}"


class FactorTributario(models.Model):
    calificacion = models.ForeignKey(CalificacionTributaria, on_delete=models.CASCADE, related_name="factores")
    columna = models.PositiveSmallIntegerField(validators=[MinValueValidator(8), MaxValueValidator(37)])
    monto_financiero = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    factor_calculado = models.DecimalField(max_digits=10, decimal_places=8, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["calificacion", "columna"], name="factor_unico_por_columna"),
        ]
        ordering = ["columna"]

    def calcular_factor(self, suma_total_montos):
        return (self.monto_financiero / suma_total_montos).quantize(OCHO_DECIMALES, rounding=ROUND_HALF_UP)

    def validar_limite_factor(self):
        return Decimal("0") <= self.factor_calculado <= Decimal("1")

    def __str__(self):
        return f"Col. {self.columna}: {self.factor_calculado}"