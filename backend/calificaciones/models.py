from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from usuarios.models import Corredora

OCHO_DECIMALES = Decimal("0.00000001")
COLUMNAS_SUMA = range(8, 20) # Columnas 8 a 19


class Emisor(models.Model):
    class Mercado(models.TextChoices):
        ACN = "ACN", "Acciones"
        CFI = "CFI", "Cuotas de fondos de inversión"
        FM = "FM", "Fondos mutuos"

    rut_emisor = models.CharField(max_length=12, unique=True)
    razon_social = models.CharField(max_length=150)
    mercado = models.CharField(max_length=3, choices=Mercado.choices)

    def validar_rut(self):
        """ Valida el digito verficador (modulo 11). Formato: 12345678-9 """
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

    def activar(self):
        self.activo = True
        self.save()

    def desactivar(self):
        self.activo = False
        self.save()

    def __str__(self):
        return self.razon_social

class Instrumento(models.Model):
    #nemotecnico es codigo corto con que se puede indentificar un instrumetno en la bolsa
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

    # relaciones

    corredora = models.ForeignKey(Corredora, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="calificaciones") # null = calificaciones de bolsa

    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="calificaciones_registradas")

    instrumento = models.ForeignKey(Instrumento, on_delete=models.PROTECT, related_name="calificaciones")

    #atributos del diagrama de clases

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

    # agregados desde el HDU

    numero_dividendo = models.PositiveIntegerField(default=0)
    tipo_sociedad = models.CharField(max_length=1, choices=TipoSociedad.choices, blank=True)


    def calcular_factores(self):
        """ Factores columna N = monto N / suma de montos de las columnas 8 a 19. """
        factores = list(self.factores.all())
        suma = sum((f.monto_financiero for f in factores if f.columna in COLUMNAS_SUMA), Decimal("0"))
        if suma == 0:
            raise ValidationError("La suma de montos de las comlumnas 8 a 19 no puede ser cero. ")
        for f in factores:
            f.factor_calculado = f.calcular_factor(suma)
            f.save(update_fields=["factor_calculado"])

    def validar_consistencia(self):
        """ Cada factor entre 0 y 1, y la suma de las colummnas 8 a 19 ≤ 1. """
        factores = list(self.factores.all())
        suma = sum((f.factor_calculado for f in factores if f.columna in COLUMNAS_SUMA), Decimal("0"))
        return suma <= 1 and all(f.validar_limite_factor() for f in factores)

    def aplicar_borrado_logico(self):
        self.activo = False
        self.save()

    def verificar_periodo_cerrado(self):
        return self.estado_periodo == self.EstadoPeriodo.CERRADO

    def __str__(self):
        return f"{self.instrumento} | {self.ejercicio_comercial} | sec . {self.secuencia_evento}"

class FactorTributario(models.Model):
    calificacion = models.ForeignKey(CalificacionTributaria, on_delete=models.CASCADE, related_name="factores")
    columna = models.PositiveSmallIntegerField(validators=[MinValueValidator(8),MaxValueValidator(37)])
    monto_financiero = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    factor_calculado = models.DecimalField(max_digits=10, decimal_places=8, default=0)

    class Meta:
        constraints = [
            #UniqueConstraint impide que exista dos tablas con los mismos valores
            models.UniqueConstraint(fields=["calificacion","columna"], name="factor_unico_por_columna"),
        ]
        ordering = ["columna"]

    def calcular_factor(self, suma_total_montos): #quantize redondea la cantidad exacta de decimal
        return (self.monto_financiero / suma_total_montos).quantize(OCHO_DECIMALES, rounding=ROUND_HALF_UP)

    def validar_limite_factor(self):
        return Decimal("0") <= self.factor_calculado <= Decimal("1")

    def __str__(self):
        return f"Col. {self.columna}: {self.factor_calculado}"