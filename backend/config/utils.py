from django.conf import settings


def obtener_ip(request):
    """IP del usuario. Detrás de Nginx (AWS) se usa la cabecera que él agrega;
    en local se usa la conexión directa, para que nadie pueda falsificarla."""
    if settings.DETRAS_DE_PROXY:
        return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
    return request.META.get("REMOTE_ADDR")