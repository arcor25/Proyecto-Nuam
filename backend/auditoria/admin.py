from django.contrib import admin, messages

from .models import BitacoraAuditoria

@admin.register(BitacoraAuditoria)
class BitacoraAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha_hora", "usuario", "accion_realizada", "entidad", "entidad_id", "ip_origen")
    list_filter = ("accion_realizada", "entidad")
    actions = ["verificar_integridad"]

    #solo lectura: nadie crea , edita ni borra desde el admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Verificar integridad de toda la bitácora")
    def verificar_integridad(self, request, queryset):
        alterados = BitacoraAuditoria.verificar_cadena()
        if alterados:
            self.message_user(request, f"Registros alterados: {alterados}", messages.ERROR)
        else:
            self.message_user(request, "La bitácora está íntegra.", messages.SUCCESS)   