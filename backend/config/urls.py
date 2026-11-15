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
from django.shortcuts import render
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from calificaciones.api import CalificacionViewSet, EmisorViewSet, InstrumentoViewSet
from calificaciones.views import catalogo, mantenedor
from cargas.api import ArchivoCSVViewSet
from rectificaciones.api import SolicitudRectificacionViewSet
from usuarios.views import LoginView, LogoutView, PerfilView, login_web, logout_web, registro_web


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"estado": "ok"})


router = DefaultRouter()
router.register("emisores", EmisorViewSet, basename="emisor")
router.register("instrumentos", InstrumentoViewSet, basename="instrumento")
router.register("calificaciones", CalificacionViewSet, basename="calificacion")
router.register("cargas", ArchivoCSVViewSet, basename="carga")
router.register("rectificaciones", SolicitudRectificacionViewSet, basename="rectificacion")

urlpatterns = [
    path("", lambda request: render(request, "inicio.html"), name="inicio"),
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/perfil/", PerfilView.as_view()),
    path("calificaciones/", mantenedor, name="mantenedor"),
    path("catalogo/", catalogo, name="catalogo"),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
    path("login/", login_web, name="login"),
    path("logout/", logout_web, name="logout"),
    path("registro/", registro_web, name="registro"),
]