from rest_framework.permissions import BasePermission


def rol_requerido(*roles):
    """Permite el acceso solo a usuarios autenticados con alguno de los roles indicados."""
    class PermisoPorRol(BasePermission):
        message = "Su rol no tiene permiso para realizar esta acción."

        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated and request.user.rol in roles)

    return PermisoPorRol