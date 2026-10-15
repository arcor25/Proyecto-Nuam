from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def mantenedor(request):
    """Pantalla del mantenedor de calificaciones (index con sus 4 modales)."""
    return render(request, "calificaciones/index.html")