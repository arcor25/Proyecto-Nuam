from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from auditoria.models import BitacoraAuditoria
from config.utils import obtener_ip

from .serializers import LoginSerializer, UsuarioPerfilSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            if token["user_id"] != request.user.pk:
                raise TokenError("El token no pertenece al usuario.")
            token.blacklist()
        except (TokenError, KeyError):
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)
        BitacoraAuditoria.registrar_evento(request.user, BitacoraAuditoria.TipoAccion.CIERRE_SESION,
                                           obtener_ip(request), "Usuario", request.user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioPerfilSerializer(request.user).data)