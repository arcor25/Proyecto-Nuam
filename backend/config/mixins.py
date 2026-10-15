from django.db import transaction

from auditoria.models import BitacoraAuditoria
from config.utils import obtener_ip


class AuditoriaMixin:
    """Registra en la bitácora cada alta, modificación y eliminación hecha por la API,
    en la misma transacción que el cambio (nunca hay cambios sin registro)."""
    entidad = ""

    def _evento(self, accion, instancia, anterior=None, nuevo=None):
        BitacoraAuditoria.registrar_evento(
            self.request.user, accion, obtener_ip(self.request), self.entidad, instancia.pk,
            valor_anterior=anterior, valor_nuevo=nuevo)

    def perform_create(self, serializer):
        with transaction.atomic():
            instancia = serializer.save()
            self._evento(BitacoraAuditoria.TipoAccion.INGRESAR, instancia, nuevo=serializer.data)

    def perform_update(self, serializer):
        anterior = self.get_serializer(serializer.instance).data
        with transaction.atomic():
            instancia = serializer.save()
            self._evento(BitacoraAuditoria.TipoAccion.MODIFICAR, instancia, anterior=anterior, nuevo=serializer.data)