from rest_framework.permissions import BasePermission


def rol_requerido(*roles):
    """Permite el acceso solo a usuarios autenticados con alguno de los roles indicados."""
    class PermisoPorRol(BasePermission):
        message = "Su rol no tiene permiso para realizar esta acción."

        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated and request.user.rol in roles)

    return PermisoPorRol


from rest_framework.permissions import SAFE_METHODS


class LecturaAutenticadaEscrituraAdminTI(BasePermission):
    """Consultar: cualquier usuario autenticado. Crear, modificar o desactivar: solo Administrador TI."""
    message = "Solo el Administrador TI puede modificar estos datos."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.rol == "ADMIN_TI"


class LecturaAutenticadaEscrituraCorredor(BasePermission):
    """Consultar: cualquier usuario autenticado. Ingresar, modificar o eliminar: solo el corredor,
    y solo calificaciones de su propia corredora."""
    message = "Solo un corredor de bolsa puede ingresar, modificar o eliminar calificaciones."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.rol == "CORREDOR"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.corredora_id != request.user.corredora_id:
            self.message = "Solo puede modificar calificaciones de su corredora. Para una de Bolsa, use Copiar."
            return False
        return True


class PermisoRectificacion(BasePermission):
    """Lectura: usuarios autenticados. Crear: solo corredor. Aprobar o rechazar: solo supervisor."""
    message = "Su rol no puede realizar esta acción sobre rectificaciones."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        if view.action == "create":
            return request.user.rol == "CORREDOR"
        if view.action in ("aprobar", "rechazar"):
            return request.user.rol == "SUPERVISOR"
        return False