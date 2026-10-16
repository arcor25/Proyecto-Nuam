from rest_framework import serializers

from calificaciones.models import CalificacionTributaria

from .models import SolicitudRectificacion


class SolicitudRectificacionSerializer(serializers.ModelSerializer):
    calificacion = serializers.PrimaryKeyRelatedField(queryset=CalificacionTributaria.objects.all())
    calificacion_detalle = serializers.SerializerMethodField()
    solicitante_email = serializers.CharField(source="solicitante.email", read_only=True)
    supervisor_email = serializers.CharField(source="supervisor.email", read_only=True, default=None)
    estado_nombre = serializers.CharField(source="get_estado_solicitud_display", read_only=True)

    class Meta:
        model = SolicitudRectificacion
        fields = ["id", "calificacion", "calificacion_detalle", "motivo_rectificacion",
                  "valores_propuestos", "valores_originales", "estado_solicitud", "estado_nombre",
                  "solicitante_email", "supervisor_email", "observacion_supervisor",
                  "fecha_solicitud", "fecha_resolucion"]
        read_only_fields = ["valores_originales", "estado_solicitud", "observacion_supervisor",
                            "fecha_solicitud", "fecha_resolucion"]

    def get_calificacion_detalle(self, obj):
        c = obj.calificacion
        return {"instrumento": c.instrumento.codigo_nemotecnico, "ejercicio_comercial": c.ejercicio_comercial,
                "secuencia_evento": c.secuencia_evento, "fecha_pago": c.fecha_pago}