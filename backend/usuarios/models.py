from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

class Corredora(models.Model):
    codigo_corredora = models.CharField(max_length=20, unique=True)
    nombre_corredora = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre_corredora

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("El mail es obligatorio")
        user = self.model(email=self.normalize_email(email),**extra)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("rol", self.model.Rol.ADMIN_TI)
        return self.create_user(email, password, **extra)

class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        CORREDOR = "CORREDOR", "Corredor de Bolsa"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        AUDITOR = "AUDITOR", "Auditor"
        ADMIN_TI = "ADMIN_TI", "Administrador TI"

    username = None
    first_name = None
    last_name = None

    # Atributos de Usuario
    rut = models.CharField(max_length=12, unique=True)
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    pais = models.CharField(max_length=50, default="Chile")
    mfa_activado = models.BooleanField(default=False)
    intentos_fallidos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CORREDOR)

    # Atributos de las subclases
    corredora = models.ForeignKey(Corredora, on_delete=models.PROTECT, null=True, blank=True, related_name="corredores")  # CorredorBolsa
    departamento = models.CharField(max_length=100, blank=True) # Supervisor
    nivel_acceso = models.CharField(max_length=20, blank=True) # AdministradorTI

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["rut", "nombre_completo"]
    objects = UsuarioManager()

    def clean(self):
        if self.rol == self.Rol.CORREDOR and not self.corredora:
            raise ValidationError("Un corredor de bolsa debe pertenecer a una corredora")

    def activar(self):
        self.is_active = True
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.save()

    def desactivar(self):
        self.is_active = False
        self.save()

    def obtener_perfil(self):
        return self.get_rol_display()

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_rol_display()})"