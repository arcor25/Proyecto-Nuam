"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from usuarios.views import LoginView, LogoutView, PerfilView

from calificaciones.views import mantenedor

from django.urls import include
from rest_framework.routers import DefaultRouter

from calificaciones.api import EmisorViewSet, InstrumentoViewSet

from calificaciones.api import CalificacionViewSet, EmisorViewSet, InstrumentoViewSet

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"estado": "ok"})

router = DefaultRouter()
router.register("emisores", EmisorViewSet, basename="emisor")
router.register("instrumentos", InstrumentoViewSet, basename="instrumento")

router.register("calificaciones", CalificacionViewSet, basename="calificacion")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/perfil/", PerfilView.as_view()),
    path("calificaciones/", mantenedor, name="mantenedor"),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),  # login para probar la API con usuarios que no son del admin
]
