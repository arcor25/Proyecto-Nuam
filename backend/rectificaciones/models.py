from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from auditoria.models import BitacoraAuditoria
from calificaciones.documentos import registrar_versiones, version_documento
from calificaciones.models import CalificacionTributaria, FactorTributario, leer_factor


class SolicitudRectificacion(models.Model):
    class EstadoSolicitud(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    # Relaciones
    calificacion = models.ForeignKey(CalificacionTributaria, on_delete=models.PROTECT,
                                     related_name="solicitudes")            # genera 1 → 0..*
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="solicitudes_enviadas")    # CorredorBolsa «solicita» 1 → 0..*
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="solicitudes_evaluadas")    # Supervisor «evalúa» 0..1

    # Atributos del diagrama
    motivo_rectificacion = models.TextField()
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estado_solicitud = models.CharField(max_length=10, choices=EstadoSolicitud.choices,
                                        default=EstadoSolicitud.PENDIENTE)
    valores_originales = models.JSONField(default=dict, blank=True)
    valores_propuestos = models.JSONField(default=dict)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    observacion_supervisor = models.TextField(blank=True)

    def clean(self):
        if self.solicitante.rol != self.solicitante.Rol.CORREDOR:
            raise ValidationError("Solo un corredor de bolsa puede solicitar una rectificación.")
        if self.calificacion.corredora_id != self.solicitante.corredora_id:
            raise ValidationError("Solo puede solicitar rectificaciones de calificaciones de su corredora.")
        if not self.calificacion.activo:
            raise ValidationError("No se puede rectificar una calificación eliminada.")
        if not self.calificacion.verificar_periodo_cerrado():  # HU-02 criterio 3 y HU-10
            raise ValidationError("La rectificación es solo para calificaciones de un período cerrado; "
                                  "las de un período abierto se modifican directamente.")
        if not self.motivo_rectificacion.strip():  # HU-10 criterio 1
            raise ValidationError("Debe indicar el motivo de la rectificación.")
        pendientes = SolicitudRectificacion.objects.filter(
            calificacion=self.calificacion, estado_solicitud=self.EstadoSolicitud.PENDIENTE).exclude(pk=self.pk)
        if pendientes.exists():
            raise ValidationError("Ya existe una solicitud pendiente para esta calificación.")
        if not self.valores_propuestos:
            raise ValidationError("Debe indicar al menos un factor propuesto.")
        for columna, valor in self.valores_propuestos.items():
            try:
                columna_num = int(columna)
            except ValueError:
                raise ValidationError(f"La columna '{columna}' no es válida.")
            if not 8 <= columna_num <= 37:
                raise ValidationError(f"La columna {columna} no existe; deben ser de la 8 a la 37.")
            factor = leer_factor(valor, columna_num)  # HU-05: número con hasta 8 decimales
            if not Decimal("0") <= factor <= Decimal("1"):
                raise ValidationError(f"El factor {columna} debe estar entre 0 y 1.")

    def registrar_solicitud(self, ip=None):
        """Guarda una copia de los factores actuales y deja la solicitud pendiente."""
        self.valores_originales = {
            str(f.columna): str(f.factor_calculado) for f in self.calificacion.factores.all()
        }
        self.estado_solicitud = self.EstadoSolicitud.PENDIENTE
        self.full_clean()
        with transaction.atomic():
            self.save()
            BitacoraAuditoria.registrar_evento(
                self.solicitante, BitacoraAuditoria.TipoAccion.RECTIFICACION, ip,
                "SolicitudRectificacion", self.pk,
                valor_nuevo={"estado": "PENDIENTE", "propuestos": self.valores_propuestos})

    def resolver_solicitud(self, supervisor, aprobada, observacion="", ip=None):
        if supervisor.rol != supervisor.Rol.SUPERVISOR:
            raise ValidationError("Solo un supervisor puede resolver solicitudes.")
        if not aprobada and not observacion.strip():
            raise ValidationError("Para rechazar una solicitud debe indicar el motivo.")

        with transaction.atomic():
            # 1. Bloquea la solicitud: otro supervisor debe esperar a que termine
            solicitud = SolicitudRectificacion.objects.select_for_update().get(pk=self.pk)
            if solicitud.estado_solicitud != self.EstadoSolicitud.PENDIENTE:
                raise ValidationError("Esta solicitud ya fue resuelta.")

            if aprobada:
                # 2. Verifica que la calificación no haya cambiado desde la solicitud
                actuales = {str(f.columna): str(f.factor_calculado) for f in self.calificacion.factores.all()}
                if actuales != self.valores_originales:
                    raise ValidationError("La calificación cambió después de la solicitud. "
                                          "El corredor debe crear una nueva solicitud.")
                for columna, valor in self.valores_propuestos.items():
                    FactorTributario.objects.update_or_create(
                        calificacion=self.calificacion, columna=int(columna),
                        defaults={"factor_calculado": leer_factor(valor, int(columna))})

                # 3. Valida las reglas e indica qué factor falla (HU-05)
                errores = self.calificacion.errores_consistencia()
                if errores:
                    raise ValidationError("Los factores propuestos no cumplen las reglas: " + "; ".join(errores))
                self.calificacion.save(update_fields=["fecha_ultima_modificacion"])

                # 4. Nueva versión en el historial de MongoDB, solo si MySQL confirma (HU-11 criterio 2)
                factores = {f.columna: f.factor_calculado for f in self.calificacion.factores.all()}
                version = version_documento(self.calificacion, factores, "RECTIFICACION", supervisor.email,
                                            f"Solicitud {self.pk}: {self.motivo_rectificacion}", timezone.now())
                transaction.on_commit(lambda: registrar_versiones([version]))

            self.supervisor = supervisor
            self.estado_solicitud = self.EstadoSolicitud.APROBADA if aprobada else self.EstadoSolicitud.RECHAZADA
            self.observacion_supervisor = observacion
            self.fecha_resolucion = timezone.now()
            self.save()

            # 5. Bitácora en la misma transacción (HU-11 criterio 3)
            BitacoraAuditoria.registrar_evento(
                supervisor, BitacoraAuditoria.TipoAccion.RECTIFICACION, ip,
                "CalificacionTributaria", self.calificacion.pk,
                valor_anterior=self.valores_originales if aprobada else None,
                valor_nuevo={"solicitud": self.pk, "estado": self.estado_solicitud,
                             "propuestos": self.valores_propuestos if aprobada else None})

    def __str__(self):
        return f"Solicitud {self.pk} - {self.calificacion} ({self.get_estado_solicitud_display()})"