from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from auditoria.models import BitacoraAuditoria
from config.mixins import AuditoriaMixin
from config.permisos import LecturaAutenticadaEscrituraAdminTI, LecturaAutenticadaEscrituraCorredor

from .models import CalificacionTributaria, Emisor, FactorTributario, Instrumento, calcular_factores_desde_montos, errores_factores
from .serializers import CalificacionSerializer, COLUMNAS, EmisorSerializer, InstrumentoSerializer, leer_monto


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


class CalificacionViewSet(AuditoriaMixin, viewsets.ModelViewSet):
    serializer_class = CalificacionSerializer
    permission_classes = [LecturaAutenticadaEscrituraCorredor]
    entidad = "CalificacionTributaria"
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        usuario = self.request.user
        consulta = (CalificacionTributaria.objects.filter(activo=True)
                    .select_related("instrumento__emisor").prefetch_related("factores")
                    .order_by("-ejercicio_comercial", "instrumento__codigo_nemotecnico", "secuencia_evento"))
        if usuario.rol == "CORREDOR":  # HU-08 criterio 3: Bolsa + su corredora
            consulta = consulta.filter(Q(corredora__isnull=True) | Q(corredora=usuario.corredora))

        p = self.request.query_params  # HU-08: filtros
        if mercado := p.get("mercado"):
            consulta = consulta.filter(instrumento__emisor__mercado=mercado.upper())
        ejercicio = p.get("ejercicio") or p.get("periodo")
        if ejercicio and ejercicio.isdigit():
            consulta = consulta.filter(ejercicio_comercial=int(ejercicio))
        origen = p.get("origen", "").upper()
        if origen == "CORREDOR":
            consulta = consulta.filter(corredora__isnull=False)
        elif origen in ("SISTEMA", "BOLSA"):
            consulta = consulta.filter(corredora__isnull=True)
        if instrumento := p.get("instrumento"):
            consulta = consulta.filter(instrumento__codigo_nemotecnico__icontains=instrumento)
        if rut := p.get("rut"):
            consulta = consulta.filter(instrumento__emisor__rut_emisor=rut.replace(".", "").upper())
        if emisor := p.get("emisor"):
            consulta = consulta.filter(instrumento__emisor__razon_social__icontains=emisor)
        if p.get("pendiente") in ("1", "true"):  # [Supuesto] con solicitud de rectificación pendiente
            consulta = consulta.filter(solicitudes__estado_solicitud="PENDIENTE").distinct()
        return consulta

    def perform_destroy(self, calificacion):
        """HU-03: borrado lógico, salvo período cerrado."""
        if calificacion.verificar_periodo_cerrado():
            raise serializers.ValidationError("La calificación pertenece a un período cerrado y no se puede eliminar.")
        with transaction.atomic():
            calificacion.aplicar_borrado_logico()
            self._evento(BitacoraAuditoria.TipoAccion.ELIMINAR, calificacion,
                         anterior={"activo": True}, nuevo={"activo": False})

    @action(detail=True, methods=["post"])
    def copiar(self, request, pk=None):
        """Crea una copia propia de la corredora a partir de la calificación seleccionada (por ejemplo, de Bolsa)."""
        origen = get_object_or_404(self.get_queryset(), pk=pk)
        usuario = request.user
        try:
            secuencia = int(request.data.get("secuencia_evento") or origen.secuencia_evento)
        except (TypeError, ValueError):
            return Response({"secuencia_evento": "Debe ser un número entero."}, status=status.HTTP_400_BAD_REQUEST)
        if secuencia < 10001:
            return Response({"secuencia_evento": "Debe ser mayor a 10.000."}, status=status.HTTP_400_BAD_REQUEST)
        llave = {"corredora": usuario.corredora, "instrumento": origen.instrumento,
                 "ejercicio_comercial": origen.ejercicio_comercial, "secuencia_evento": secuencia}
        if CalificacionTributaria.objects.filter(**llave).exists():
            return Response({"detail": "Su corredora ya tiene una calificación con esa llave. "
                                       "Indique otra secuencia_evento."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            copia = CalificacionTributaria.objects.create(
                **llave, fecha_pago=origen.fecha_pago, valor_historico=origen.valor_historico,
                descripcion=origen.descripcion, is_fut=origen.is_fut,
                factor_actualizacion=origen.factor_actualizacion, numero_dividendo=origen.numero_dividendo,
                tipo_sociedad=origen.tipo_sociedad, registrado_por=usuario,
                origen_dato=CalificacionTributaria.FormaActualizacion.INGRESO_MANUAL)
            FactorTributario.objects.bulk_create([
                FactorTributario(calificacion=copia, columna=f.columna, monto_financiero=f.monto_financiero,
                                 factor_calculado=f.factor_calculado) for f in origen.factores.all()])
            self._evento(BitacoraAuditoria.TipoAccion.INGRESAR, copia, nuevo={"copia_de": origen.pk})
        return Response(self.get_serializer(copia).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def calcular(self, request):
        """HU-04: calcula los factores desde los montos, sin guardar (botón Calcular)."""
        errores, montos = {}, {}
        for columna in COLUMNAS:
            clave = f"f{columna:02d}"
            try:
                montos[columna] = leer_monto(request.data.get(clave, ""))
            except ValueError as error:
                errores[clave] = str(error)
        if errores:
            return Response(errores, status=status.HTTP_400_BAD_REQUEST)
        try:
            factores = calcular_factores_desde_montos(montos)
        except DjangoValidationError as error:
            return Response({"factores": error.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"factores": {str(c): str(v) for c, v in factores.items()},
                         "errores": errores_factores(factores)})