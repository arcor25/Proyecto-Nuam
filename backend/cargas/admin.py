from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import ArchivoCSV

@admin.register(ArchivoCSV)
class ArchivoCSVAdmin(admin.ModelAdmin):
    list_display = ("nombre_archivo", "formato_tipo", "estado_carga", "total_filas",
                    "filas_validas", "filas_rechazadas", "cargado_por", "fecha_carga")

    list_filter = ("formato_tipo", "estado_carga")
    readonly_fields = ("nombre_archivo", "tamano_bytes", "total_filas", "filas_validas",
                       "filas_rechazadas", "estado_carga", "fecha_carga")

    actions = ["procesar_archivos"]

    @admin.action(description="Procesar archivos seleccionados")
    def procesar_archivos(self, request, queryset):
        for archivo in queryset:
            try:
                errores = archivo.procesar_lote()
            except ValidationError as error:
                self.message_user(request, f"{archivo}: {error.messages[0]}", "messages.ERROR")
                continue
        if errores:
            self.message_user(request, f"{archivo}: {len(errores)} fila(s) rechazada(s)."
                              + " | ".join(errores[:5]), messages.WARNING)
        else:
            self.message_user(request, f"{archivo}: {archivo.filas_validas} fila(s) cargada(s).",
                              messages.SUCCESS)
