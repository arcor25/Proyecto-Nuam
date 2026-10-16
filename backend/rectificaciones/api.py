from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permisos import PermisoRectificacion
from config.utils import obtener_ip

from .models import SolicitudRectificacion
from .serializers import SolicitudRectificacionSerializer


class SolicitudRectificacionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                                    mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SolicitudRectificacionSerializer
    permission_classes = [PermisoRectificacion]

    def get_queryset(self):
        usuario = self.request.user
        consulta = SolicitudRectificacion.objects.select_related(
            "calificacion__instrumento", "solicitante", "supervisor").order_by("-fecha_solicitud")
        if usuario.rol == "CORREDOR":  # solo las suyas
            consulta = consulta.filter(solicitante=usuario)
        if estado := self.request.query_params.get("estado"):
            consulta = consulta.filter(estado_solicitud=estado.upper())
        return consulta

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        calificacion = serializer.validated_data["calificacion"]
        if calificacion.corredora_id != request.user.corredora_id:
            return Response({"calificacion": "Solo puede solicitar rectificaciones de su corredora."},
                            status=status.HTTP_403_FORBIDDEN)
        solicitud = SolicitudRectificacion(
            calificacion=calificacion, solicitante=request.user,
            motivo_rectificacion=serializer.validated_data["motivo_rectificacion"],
            valores_propuestos=serializer.validated_data["valores_propuestos"])
        try:
            solicitud.registrar_solicitud(ip=obtener_ip(request))
        except DjangoValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(solicitud).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        solicitud = self.get_object()
        try:
            solicitud.resolver_solicitud(request.user, aprobada=True,
                                         observacion=request.data.get("observacion", ""),
                                         ip=obtener_ip(request))
        except DjangoValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        solicitud.refresh_from_db()
        return Response(self.get_serializer(solicitud).data)

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        solicitud = self.get_object()
        try:
            solicitud.resolver_solicitud(request.user, aprobada=False,
                                         observacion=request.data.get("observacion", ""),
                                         ip=obtener_ip(request))
        except DjangoValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        solicitud.refresh_from_db()
        return Response(self.get_serializer(solicitud).data)