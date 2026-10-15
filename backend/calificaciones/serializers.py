from rest_framework import serializers

from .models import Emisor, Instrumento


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