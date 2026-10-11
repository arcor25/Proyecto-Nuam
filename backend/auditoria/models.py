import hashlib
import hmac
import json


from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.utils import timezone

from calificaciones.models import CalificacionTributaria

HASH_INICIAL = "0" * 64

class BitacoraQuerySet(models.QuerySet):
    """ Bloquea las modificaciones y eliminaciones masivas. """

    def update(self, **kwargs):
        raise ValidationError("La bitacora es inmutable: no se permiten modificaciones.")

    def delete(self):
        raise ValidationError("La bitacora es inmutable: no se permiten eliminaciones.")


class BitacoraAuditoria(models.Model):
    class TipoAccion(models.TextChoices):
        INGRESAR = "INGRESAR", "Ingresar"
        MODIFICAR = "MODIFICAR", "Modificar"
        ELIMINAR = "ELIMINAR", "Eliminar"
        CARGA_MASIVA = "CARGA_MASIVA", "Carga masiva"
        RECTIFICACION = "RECTIFICACION", "Rectificacion"
        INICIO_SESION = "INICIO_SESION", "Inicio de sesion"
        CIERRE_SESION = "CIERRA_SESION", "Cierra de sesion"
        GESTION_USUARIO = "GESTION_USUARIO", "Gestion de usuario"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="eventos_auditoria")

    #Atributos
    accion_realizada = models.CharField(max_length=20, choices=TipoAccion.choices)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now, editable=False)
    forma_actualizacion = models.CharField(max_length=20, blank=True,
                                           choices=CalificacionTributaria.FormaActualizacion.choices)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    hash_sha256 = models.CharField(max_length=64, editable=False)

    #Agregados: sobre que registro fue la accion
    entidad = models.CharField(max_length=50, blank=True)
    entidad_id = models.PositiveIntegerField(null=True, blank=True)

    objects = BitacoraQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    #registro
    
    @classmethod
    def registrar_evento(cls , usuario, accion, ip=None, entidad="", entidad_id=None,
                         forma="", valor_anterior=None, valor_nuevo=None):
        """ Crea un evento nuevo. Es la unica forma de escribir en la bitacora """
        def a_texto(valor):
            return json.dumps(valor, sort_keys=True, ensure_ascii=False, default=str) if valor else ""


        evento = cls(usuario=usuario, accion_realizada=accion, ip_origen=ip, entidad=entidad,
                     entidad_id=entidad_id, forma_actualizacion=forma, valor_anterior=a_texto(valor_anterior),
                     valor_nuevo=a_texto(valor_nuevo))
        evento.save()
        return evento

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("La bitacora es inmutable: no se permiten modificaciones.")
        with transaction.atomic():
            ultimo = BitacoraAuditoria.objects.select_for_update().order_by("-id").first()
            hash_previo = ultimo.hash_sha256 if ultimo else HASH_INICIAL
            self.hash_sha256 = self._calcular_hash(hash_previo)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La bitacora es inmutable: no se permiten eliminaciones. ")

    #hash
    
    def _hash_previo(self):
        previo = BitacoraAuditoria.objects.filter(id__lt=self.id).order_by("-id").first()
        return previo.hash_sha256 if previo else HASH_INICIAL

    def _calcular_hash(self, hash_previo):
        clave = getattr(settings, "AUDITORIA_HMAC_KEY", None)
        if not clave:
            raise ImproperlyConfigured("Falta AUDITORIA_HMAC_KEY en el archivo .env")
        datos = "|".join([
            hash_previo, str(self.usuario_id), self.accion_realizada, str(self.ip_origen or ""),
            self.fecha_hora.isoformat(), self.forma_actualizacion, self.entidad,
            str(self.entidad_id or ""), self.valor_anterior, self.valor_nuevo,
        ])
        return hmac.new(clave.encode("utf-8"), datos.encode("utf-8"), hashlib.sha256).hexdigest()


    def verificar_integridad_hash(self):
        return hmac.compare_digest(self.hash_sha256, self._calcular_hash(self._hash_previo()))

    @classmethod
    def verificar_cadena(cls):
        """ Devuelve los id de los registros alterados (lista vacia = todo integro). """
        alterados, hash_previo = [], HASH_INICIAL
        for evento in cls.objects.order_by("id").iterator():
            if not hmac.compare_digest(evento.hash_sha256, evento._calcular_hash(hash_previo)):
                alterados.append(evento.id)
            hash_previo = evento.hash_sha256
        return alterados

    def __str__(self):
        return f"#{self.id} {self.fecha_hora:%d-%m-%Y %H:%M} {self.usuario} - {self.get_accion_realizada_display()}"