from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.utils import obtener_ip

from .documentos import obtener_resultado_carga
from .models import ArchivoCSV
from .serializers import ArchivoCSVSerializer


class ArchivoCSVViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                        mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ArchivoCSVSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user
        consulta = ArchivoCSV.objects.select_related("cargado_por").order_by("-fecha_carga")
        if usuario.rol == "CORREDOR":  # solo las cargas de su corredora
            consulta = consulta.filter(cargado_por__corredora=usuario.corredora)
        if estado := self.request.query_params.get("estado"):
            consulta = consulta.filter(estado_carga=estado.upper())
        return consulta

    # ---------- Reglas de acceso ----------
    def _exigir_corredor(self):
        if self.request.user.rol != "CORREDOR":
            raise PermissionDenied("Solo un corredor de bolsa puede cargar archivos.")

    def _archivo_propio(self):
        archivo = self.get_object()
        if archivo.cargado_por_id != self.request.user.pk:
            raise PermissionDenied("Solo quien subió el archivo puede validarlo o procesarlo.")
        return archivo

    # ---------- Subir y previsualizar ----------
    def create(self, request, *args, **kwargs):
        self._exigir_corredor()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        archivo = serializer.save(cargado_por=request.user)
        filas = archivo._leer_filas()
        formato_valido = archivo.validar_formato(filas)
        archivo.save(update_fields=["total_filas"])
        return Response({**self.get_serializer(archivo).data,
                         "formato_valido": formato_valido,
                         "previsualizacion": {"encabezado": filas[0] if filas else [], "filas": filas[1:11]}},
                        status=status.HTTP_201_CREATED)

    # ---------- Detalle con el resultado de MongoDB ----------
    def retrieve(self, request, *args, **kwargs):
        archivo = self.get_object()
        return Response({**self.get_serializer(archivo).data,
                         "resultado": obtener_resultado_carga(archivo.pk)})

    # ---------- Calcular factores / validar sin guardar ----------
    @action(detail=True, methods=["post"])
    def validar(self, request, pk=None):
        self._exigir_corredor()
        archivo = self._archivo_propio()
        return Response({**archivo.validar_lote(), "estado_carga": archivo.estado_carga})

    # ---------- Grabar ----------
    @action(detail=True, methods=["post"])
    def procesar(self, request, pk=None):
        self._exigir_corredor()
        archivo = self._archivo_propio()
        try:
            errores = archivo.procesar_lote(ip=obtener_ip(request))
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        resultado = obtener_resultado_carga(archivo.pk) or {}
        return Response({**self.get_serializer(archivo).data,
                         "resumen": resultado.get("resumen"), "errores": errores})