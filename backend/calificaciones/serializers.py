from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .documentos import registrar_versiones, version_documento
from .models import (CalificacionTributaria, Emisor, FactorTributario, Instrumento,
                     calcular_factores_desde_montos, errores_factores, leer_factor)

COLUMNAS = range(8, 38)
MONTO_MAXIMO = Decimal("1000000000000")

class EmisorSerializer(serializers.ModelSerializer):
    mercado_nombre = serializers.CharField(source="get_mercado_display", read_only=True)

    class Meta:
        model = Emisor
        fields = ["id", "rut_emisor", "razon_social", "mercado", "mercado_nombre", "activo"]
        read_only_fields = ["activo"]  # se cambia solo con desactivar/activar

    def validate_rut_emisor(self, valor):
        valor = valor.replace(".", "").strip().upper()
        if not Emisor(rut_emisor=valor).validar_rut():  # HU-16 criterio 1
            raise serializers.ValidationError("El RUT del emisor no es válido: revise el dígito verificador.")
        return valor

def leer_monto(texto):
    """Convierte un monto ingresado (punto o coma decimal, sin separador de miles)."""
    limpio = str(texto).strip() or "0"
    if "," in limpio and "." in limpio:
        raise ValueError("tiene separador de miles")
    try:
        valor = Decimal(limpio.replace(",", ".")).quantize(Decimal("0.00000001"))
    except InvalidOperation:
        raise ValueError(f"'{texto}' no es un monto válido")
    if valor < 0 or valor >= MONTO_MAXIMO:
        raise ValueError(f"'{texto}' está fuera de rango")
    return valor


def leer_columnas(datos, por_montos):
    """Lee f08 a f37 del formulario. Devuelve (factores, montos) o lanza un error por campo."""
    errores, valores = {}, {}
    for columna in COLUMNAS:
        clave = f"f{columna:02d}"
        texto = datos.get(clave, "")
        try:
            valores[columna] = leer_monto(texto) if por_montos else leer_factor(texto, columna)
        except ValueError as error:
            errores[clave] = str(error)
        except DjangoValidationError as error:
            errores[clave] = error.messages[0]
    if errores:
        raise serializers.ValidationError(errores)
    try:
        factores = calcular_factores_desde_montos(valores) if por_montos else valores
    except DjangoValidationError as error:
        raise serializers.ValidationError({"factores": error.messages})
    reglas = errores_factores(factores)  # HU-05: indica qué factor falla
    if reglas:
        raise serializers.ValidationError({"factores": reglas})
    return factores, (valores if por_montos else None)


def es_verdadero(valor):
    return str(valor).strip().lower() in ("true", "1", "on", "si", "sí")


class CalificacionSerializer(serializers.ModelSerializer):
    # Escritura
    instrumento = serializers.SlugRelatedField(
        slug_field="codigo_nemotecnico",
        queryset=Instrumento.objects.filter(emisor__activo=True)) 
    mercado = serializers.CharField(write_only=True, required=False)
    ingreso_montos = serializers.BooleanField(write_only=True, required=False, default=False)
    is_fut = serializers.BooleanField(required=True)  # HU-01 criterio 1

    # Lectura
    mercado_codigo = serializers.CharField(source="instrumento.emisor.mercado", read_only=True)
    emisor = serializers.CharField(source="instrumento.emisor.razon_social", read_only=True)
    rut_emisor = serializers.CharField(source="instrumento.emisor.rut_emisor", read_only=True)
    origen = serializers.SerializerMethodField()
    origen_dato_nombre = serializers.CharField(source="get_origen_dato_display", read_only=True)
    factores = serializers.SerializerMethodField()
    montos = serializers.SerializerMethodField()

    class Meta:
        model = CalificacionTributaria
        fields = ["id", "instrumento", "mercado", "mercado_codigo", "emisor", "rut_emisor",
                  "ejercicio_comercial", "secuencia_evento", "fecha_pago", "numero_dividendo", "tipo_sociedad",
                  "valor_historico", "descripcion", "is_fut", "factor_actualizacion", "ingreso_montos",
                  "origen", "origen_dato", "origen_dato_nombre", "estado_periodo",
                  "fecha_ultima_modificacion", "factores", "montos"]
        read_only_fields = ["origen_dato", "estado_periodo", "fecha_ultima_modificacion"]
        extra_kwargs = {"valor_historico": {"required": True},        # HU-01 criterio 1
                        "factor_actualizacion": {"required": True}}
        validators = []  # la llave única se valida en create() con un mensaje claro

    # ---------- Lectura ----------
    def get_origen(self, obj):
        return "CORREDOR" if obj.corredora_id else "SISTEMA"

    def get_factores(self, obj):
        return {str(f.columna): str(f.factor_calculado) for f in obj.factores.all()}

    def get_montos(self, obj):
        return {str(f.columna): str(f.monto_financiero) for f in obj.factores.all()}

    # ---------- Validación ----------
    def validate(self, attrs):
        instrumento = attrs.get("instrumento") or (self.instance.instrumento if self.instance else None)
        mercado = attrs.pop("mercado", None)
        if mercado and instrumento and instrumento.emisor.mercado != mercado.strip().upper():
            raise serializers.ValidationError({"mercado": "No corresponde al mercado del instrumento."})

        if self.instance:
            if self.instance.verificar_periodo_cerrado():  # HU-02 criterio 3
                raise serializers.ValidationError(
                    "La calificación pertenece a un período cerrado: solicite una rectificación.")
            for campo in ("instrumento", "ejercicio_comercial", "secuencia_evento"):
                if campo in attrs and attrs[campo] != getattr(self.instance, campo):
                    raise serializers.ValidationError({campo: "Forma parte de la llave y no se puede modificar."})

        claves = [f"f{c:02d}" for c in COLUMNAS]
        if self.partial and not any(clave in self.initial_data for clave in claves):
            attrs["_factores"], attrs["_montos"] = None, None  # modificación sin tocar factores
        else:
            por_montos = es_verdadero(self.initial_data.get("ingreso_montos", False))
            attrs["_factores"], attrs["_montos"] = leer_columnas(self.initial_data, por_montos)
        attrs.pop("ingreso_montos", None)
        return attrs

    # ---------- Guardado ----------
    def _guardar_factores(self, calificacion, factores, montos):
        calificacion.factores.all().delete()
        FactorTributario.objects.bulk_create([
            FactorTributario(calificacion=calificacion, columna=c, factor_calculado=factores[c],
                             monto_financiero=montos[c] if montos else Decimal("0"))
            for c in COLUMNAS])

    def _registrar_version(self, calificacion, factores, motivo):
        usuario = self.context["request"].user
        version = version_documento(calificacion, factores, calificacion.origen_dato, usuario.email,
                                    motivo, timezone.now())
        transaction.on_commit(lambda: registrar_versiones([version]))  # MongoDB solo si MySQL confirma

    def create(self, datos):
        factores, montos = datos.pop("_factores"), datos.pop("_montos")
        usuario = self.context["request"].user
        llave = {"corredora": usuario.corredora, "instrumento": datos["instrumento"],
                 "ejercicio_comercial": datos["ejercicio_comercial"],
                 "secuencia_evento": datos["secuencia_evento"]}
        existente = CalificacionTributaria.objects.filter(**llave).first()
        if existente and existente.activo:
            raise serializers.ValidationError(
                "Su corredora ya tiene una calificación con ese instrumento, año y secuencia.")
        if existente:  # estaba eliminada (borrado lógico): se reactiva con los datos nuevos
            for campo, valor in datos.items():
                setattr(existente, campo, valor)
            calificacion = existente
            calificacion.activo = True
        else:
            calificacion = CalificacionTributaria(**datos, corredora=usuario.corredora)
        calificacion.registrado_por = usuario
        calificacion.origen_dato = CalificacionTributaria.FormaActualizacion.INGRESO_MANUAL
        calificacion.save()
        self._guardar_factores(calificacion, factores, montos)
        self._registrar_version(calificacion, factores, "Ingreso manual")
        return calificacion

    def update(self, calificacion, datos):
        factores, montos = datos.pop("_factores"), datos.pop("_montos")
        for campo, valor in datos.items():
            setattr(calificacion, campo, valor)
        calificacion.registrado_por = self.context["request"].user
        calificacion.origen_dato = CalificacionTributaria.FormaActualizacion.INGRESO_MANUAL
        calificacion.save()
        if factores is not None:
            self._guardar_factores(calificacion, factores, montos)
            self._registrar_version(calificacion, factores, "Modificación manual")
        calificacion._prefetched_objects_cache = {}  # para devolver los factores actualizados
        return calificacion

class InstrumentoSerializer(serializers.ModelSerializer):
    emisor_razon_social = serializers.CharField(source="emisor.razon_social", read_only=True)
    mercado = serializers.CharField(source="emisor.mercado", read_only=True)

    class Meta:
        model = Instrumento
        fields = ["id", "codigo_nemotecnico", "descripcion", "esta_inscrito",
                  "emisor", "emisor_razon_social", "mercado"]
        read_only_fields = ["esta_inscrito"]

    def validate_codigo_nemotecnico(self, valor):
        return valor.strip().upper()

    def validate_emisor(self, emisor):
        if not emisor.activo:  # HU-17 criterio 2
            raise serializers.ValidationError("El emisor está desactivado.")
        return emisor


