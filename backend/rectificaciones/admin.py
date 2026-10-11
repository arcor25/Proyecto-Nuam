from django.contrib import admin
from .models import SolicitudRectificacion


@admin.register(SolicitudRectificacion)
class SolicitudRectificacionAdmin(admin.ModelAdmin):
    list_display = ("id", "calificacion", "solicitante", "estado_solicitud", "fecha_solicitud", "supervisor")
    list_filter = ("estado_solicitud",)
    readonly_fields = ("valores_originales", "fecha_solicitud", "fecha_resolucion")
