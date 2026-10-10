from django.contrib import admin
from .models import Emisor, Instrumento, CalificacionTributaria, FactorTributario

#FactorInline muestra los factores dentro de la pantalla de cada calificacion
class FactorInline(admin.TabularInline):
    model = FactorTributario
    extra = 0

@admin.register(CalificacionTributaria)
class CalificacionAdmin(admin.ModelAdmin):
    #el list_display muestra la tabla de colummna
    list_display = ("instrumento","ejercicio_comercial", "fecha_pago", "origen_dato", "corredora", "activo")
    list_filter = ("ejercicio_comercial", "origen_dato", "activo")
    inlines = [FactorInline]


admin.site.register(Emisor)
admin.site.register(Instrumento)
