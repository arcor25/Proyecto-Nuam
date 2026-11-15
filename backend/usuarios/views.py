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

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as CoreValidationError
from django.core.validators import validate_email
from calificaciones.models import Emisor
from .models import Corredora, Usuario

def registro_web(request):
    es_admin = request.user.is_authenticated and request.user.rol == Usuario.Rol.ADMIN_TI
    corredoras = Corredora.objects.order_by("nombre_corredora")
    roles = Usuario.Rol.choices if es_admin else [(Usuario.Rol.CORREDOR, "Corredor de Bolsa")]
    contexto = {
        "corredoras": corredoras,
        "roles": roles,
        "es_admin": es_admin,
        "valores": {},
        "errores": {},
        "enviado": False,
    }

    if request.method == "GET":
        return render(request, "usuarios/registro.html", contexto)

    datos = {k: request.POST.get(k, "").strip() for k in (
        "rut", "nombre_completo", "email", "rol", "pais",
        "corredora_id", "nueva_corredora_codigo", "nueva_corredora_nombre"
    )}
    if not es_admin:
        datos["rol"] = Usuario.Rol.CORREDOR

    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    rut_limpio = datos["rut"].replace(".", "").upper()
    errores = {}

    if not rut_limpio or not Emisor(rut_emisor=rut_limpio).validar_rut():
        errores["rut"] = "Ingrese un RUT válido con guion (ej. 19876543-0)."
    elif Usuario.objects.filter(rut=rut_limpio).exists():
        errores["rut"] = "Este RUT ya se encuentra registrado."

    if len(datos["nombre_completo"]) < 3:
        errores["nombre_completo"] = "Ingrese su nombre completo (mínimo 3 caracteres)."

    try:
        validate_email(datos["email"])
        if Usuario.objects.filter(email__iexact=datos["email"]).exists():
            errores["email"] = "Este correo ya está registrado."
    except CoreValidationError:
        errores["email"] = "Ingrese un correo electrónico válido."

    if datos["rol"] not in Usuario.Rol.values:
        errores["rol"] = "Seleccione un rol válido."

    corredora = None
    if datos["rol"] == Usuario.Rol.CORREDOR:
        if datos["corredora_id"]:
            corredora = Corredora.objects.filter(pk=datos["corredora_id"]).first()
            if not corredora:
                errores["corredora"] = "La corredora seleccionada no existe."
        elif datos["nueva_corredora_codigo"] and datos["nueva_corredora_nombre"]:
            corredora, _ = Corredora.objects.get_or_create(
                codigo_corredora=datos["nueva_corredora_codigo"].upper(),
                defaults={"nombre_corredora": datos["nueva_corredora_nombre"]},
            )
        else:
            errores["corredora"] = "Seleccione una corredora o ingrese código y nombre para crear una."

    try:
        validate_password(password)
    except CoreValidationError as exc:
        errores["password"] = " ".join(exc.messages)

    if password != password_confirm:
        errores["password_confirm"] = "Las contraseñas no coinciden."

    contexto.update({"valores": datos, "errores": errores, "enviado": True})
    if errores:
        return render(request, "usuarios/registro.html", contexto, status=400)

    usuario = Usuario.objects.create_user(
        email=datos["email"],
        password=password,
        rut=rut_limpio,
        nombre_completo=datos["nombre_completo"],
        rol=datos["rol"],
        pais=datos["pais"] or "Chile",
        corredora=corredora,
    )
    if request.user.is_authenticated:
        BitacoraAuditoria.registrar_evento(
            request.user, BitacoraAuditoria.TipoAccion.GESTION_USUARIO,
            obtener_ip(request), "Usuario", usuario.pk,
            valor_nuevo={"email": usuario.email, "rol": usuario.rol},
        )

    return render(request, "usuarios/registro.html", {
        "corredoras": Corredora.objects.order_by("nombre_corredora"),
        "roles": roles,
        "es_admin": es_admin,
        "valores": {},
        "errores": {},
        "enviado": False,
        "exito": f"Usuario {usuario.nombre_completo} ({usuario.get_rol_display()}) creado correctamente.",
    })