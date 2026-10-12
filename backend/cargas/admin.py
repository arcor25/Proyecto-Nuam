from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .documentos import obtener_resultado_carga
from .models import ArchivoCSV


@admin.register(ArchivoCSV)
class ArchivoCSVAdmin(admin.ModelAdmin):
    list_display = ("nombre_archivo", "formato_tipo", "estado_carga", "total_filas",
                    "filas_validas", "filas_rechazadas", "cargado_por", "fecha_carga")
    list_filter = ("formato_tipo", "estado_carga")
    readonly_fields = ("nombre_archivo", "tamano_bytes", "total_filas", "filas_validas",
                       "filas_rechazadas", "estado_carga", "fecha_carga", "detalle_mongo")
    actions = ["procesar_archivos"]

    @admin.display(description="Detalle de la carga (MongoDB)")
    def detalle_mongo(self, obj):
        resultado = obtener_resultado_carga(obj.pk) if obj.pk else None
        if not resultado:
            return "Sin detalle registrado (archivo no procesado o MongoDB no disponible)."
        r = resultado.get("resumen", {})
        lineas = [f"Creadas: {r.get('creadas', 0)} · Actualizadas: {r.get('actualizadas', 0)} · "
                  f"Rechazadas: {r.get('rechazadas', 0)}"] + resultado.get("errores", [])[:50]
        return format_html_join(mark_safe("<br>"), "{}", ((linea,) for linea in lineas))

    @admin.action(description="Procesar archivos seleccionados")
    def procesar_archivos(self, request, queryset):
        for archivo in queryset:
            try:
                errores = archivo.procesar_lote()
            except ValidationError as error:
                self.message_user(request, f"{archivo}: {error.messages[0]}", messages.ERROR)
                continue
            if errores:
                self.message_user(request, f"{archivo}: {len(errores)} fila(s) rechazada(s). "
                                           + " | ".join(errores[:5]), messages.WARNING)
            else:
                self.message_user(request, f"{archivo}: {archivo.filas_validas} fila(s) cargada(s).",
                                  messages.SUCCESS)