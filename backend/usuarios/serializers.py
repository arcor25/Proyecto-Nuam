from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from auditoria.models import BitacoraAuditoria
from config.utils import obtener_ip

from .models import Usuario

MENSAJE_GENERICO = "Credenciales inválidas o cuenta bloqueada temporalmente."


class UsuarioPerfilSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source="get_rol_display", read_only=True)
    corredora_nombre = serializers.CharField(source="corredora.nombre_corredora", read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = ["id", "email", "rut", "nombre_completo", "rol", "rol_nombre",
                  "corredora", "corredora_nombre", "pais", "mfa_activado"]


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = user.rol  # el frontend lo usa para mostrar u ocultar opciones
        return token

    def validate(self, attrs):
        ip = obtener_ip(self.context["request"])
        usuario = Usuario.objects.filter(email__iexact=attrs.get("email", "").strip()).first()
        ahora = timezone.now()

        if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
            raise AuthenticationFailed(MENSAJE_GENERICO)

        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            if usuario:
                self._registrar_fallo(usuario, ip, ahora)
            raise AuthenticationFailed(MENSAJE_GENERICO)

        Usuario.objects.filter(pk=self.user.pk).update(intentos_fallidos=0, bloqueado_hasta=None)
        BitacoraAuditoria.registrar_evento(self.user, BitacoraAuditoria.TipoAccion.INICIO_SESION, ip,
                                           "Usuario", self.user.pk, valor_nuevo={"resultado": "exitoso"})
        data["usuario"] = UsuarioPerfilSerializer(self.user).data
        return data

    @staticmethod
    def _registrar_fallo(usuario, ip, ahora):
        # F() suma en la base de datos: dos intentos simultáneos no se pisan
        Usuario.objects.filter(pk=usuario.pk).update(intentos_fallidos=F("intentos_fallidos") + 1)
        usuario.refresh_from_db(fields=["intentos_fallidos"])
        bloqueado = usuario.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS
        if bloqueado:
            Usuario.objects.filter(pk=usuario.pk).update(
                intentos_fallidos=0,
                bloqueado_hasta=ahora + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS))
        BitacoraAuditoria.registrar_evento(usuario, BitacoraAuditoria.TipoAccion.INICIO_SESION, ip,
                                           "Usuario", usuario.pk,
                                           valor_nuevo={"resultado": "fallido", "bloqueado": bloqueado})