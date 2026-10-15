from django.db import transaction
from rest_framework import viewsets

from auditoria.models import BitacoraAuditoria
from config.mixins import AuditoriaMixin
from config.permisos import LecturaAutenticadaEscrituraAdminTI

from .models import Emisor, Instrumento
from .serializers import EmisorSerializer, InstrumentoSerializer


class EmisorViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    serializer_class = EmisorSerializer
    permission_classes = [LecturaAutenticadaEscrituraAdminTI]
    entidad = "Emisor"

    def get_queryset(self):
        consulta = Emisor.objects.order_by("razon_social")
        # HU-17 criterio 2: los inactivos no aparecen, salvo que el administrador los pida
        if self.request.query_params.get("incluir_inactivos") != "1":
            consulta = consulta.filter(activo=True)
        if mercado := self.request.query_params.get("mercado"):
            consulta = consulta.filter(mercado=mercado)
        return consulta

    def perform_destroy(self, instancia):
        """HU-17: no se borra, se desactiva."""
        with transaction.atomic():
            instancia.desactivar()
            self._evento(BitacoraAuditoria.TipoAccion.ELIMINAR, instancia,
                         anterior={"activo": True}, nuevo={"activo": False})


class InstrumentoViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    serializer_class = InstrumentoSerializer
    permission_classes = [LecturaAutenticadaEscrituraAdminTI]
    entidad = "Instrumento"

    def get_queryset(self):
        consulta = Instrumento.objects.select_related("emisor").order_by("codigo_nemotecnico")
        if self.request.query_params.get("incluir_inactivos") != "1":
            consulta = consulta.filter(esta_inscrito=True, emisor__activo=True)
        if mercado := self.request.query_params.get("mercado"):
            consulta = consulta.filter(emisor__mercado=mercado)
        return consulta

    def perform_destroy(self, instancia):
        """Desinscribe el instrumento en vez de borrarlo (conserva las calificaciones asociadas)."""
        with transaction.atomic():
            instancia.desinscribir()
            self._evento(BitacoraAuditoria.TipoAccion.ELIMINAR, instancia,
                         anterior={"esta_inscrito": True}, nuevo={"esta_inscrito": False})