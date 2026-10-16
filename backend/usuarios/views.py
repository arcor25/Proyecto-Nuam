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

from django.contrib.auth import BACKEND_SESSION_KEY, login as django_login, logout as django_logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .serializers import LoginSerializer


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


from rest_framework.exceptions import AuthenticationFailed, ValidationError as DRFValidationError

def login_web(request):
    """Pantalla de inicio de sesión del mantenedor. Usa el mismo control de intentos y
    bloqueo (HU-13) que la API, y crea una sesión de Django."""
    if request.method == "GET":
        return render(request, "usuarios/login.html", {"siguiente": request.GET.get("next", "")})

    email = request.POST.get("email", "")
    siguiente = request.POST.get("next", "")
    serializer = LoginSerializer(
        data={"email": email, "password": request.POST.get("password", "")},
        context={"request": request},
    )
    try:
        serializer.is_valid(raise_exception=True)
    except (AuthenticationFailed, DRFValidationError):
        return render(request, "usuarios/login.html",
                      {"error": "Credenciales inválidas o cuenta bloqueada temporalmente.",
                       "email": email, "siguiente": siguiente}, status=401)

    django_login(request, serializer.user, backend="django.contrib.auth.backends.ModelBackend")
    destino = siguiente if url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}) else "/calificaciones/"
    return redirect(destino)


@require_http_methods(["POST"])
def logout_web(request):
    django_logout(request)
    return redirect("/login/")