from django.conf import settings
from rest_framework import serializers

from .models import ArchivoCSV


class ArchivoCSVSerializer(serializers.ModelSerializer):
    cargado_por = serializers.CharField(source="cargado_por.email", read_only=True)
    formato_tipo_nombre = serializers.CharField(source="get_formato_tipo_display", read_only=True)
    estado_carga_nombre = serializers.CharField(source="get_estado_carga_display", read_only=True)
    archivo = serializers.FileField(write_only=True)

    class Meta:
        model = ArchivoCSV
        fields = ["id", "archivo", "nombre_archivo", "tamano_bytes", "formato_tipo", "formato_tipo_nombre",
                  "estado_carga", "estado_carga_nombre", "total_filas", "filas_validas", "filas_rechazadas",
                  "cargado_por", "fecha_carga"]
        read_only_fields = ["nombre_archivo", "tamano_bytes", "estado_carga", "total_filas",
                            "filas_validas", "filas_rechazadas", "fecha_carga"]

    def validate_archivo(self, archivo):
        """Se rechaza antes de guardar en disco (HU-06)."""
        if not archivo.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Solo se aceptan archivos .csv.")
        if archivo.size > settings.CSV_TAMANO_MAXIMO_MB * 1024 * 1024:
            raise serializers.ValidationError(f"El archivo supera el máximo de {settings.CSV_TAMANO_MAXIMO_MB} MB.")
        if archivo.size == 0:
            raise serializers.ValidationError("El archivo está vacío.")
        return archivo