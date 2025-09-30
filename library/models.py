from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


def renombrar_archivo(instance, filename):
    extension = filename.split('.')[-1]
    nombre_limpio = instance.titulo.replace(' ', '_')
    return f'libros/{nombre_limpio}.{extension}'


class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="libros")
    portada = models.ImageField(upload_to="portadas/", blank=True, null=True)
    archivo = models.FileField(upload_to="libros/", blank=True, null=True)
    año = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.titulo} - {self.autor}"
class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)



class CustomUser(AbstractBaseUser, PermissionsMixin):
    name  = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    rol   = models.ForeignKey(Rol, on_delete=models.CASCADE)
    categorias = models.ManyToManyField(
        Categoria,
        through="CategoriaPermitida",
        blank=True,
        related_name="usuarios"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} - {self.rol.nombre if self.rol else 'Sin rol'}"


class Material(models.Model):
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    profesor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo


class CategoriaPermitida(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('usuario', 'categoria')
        verbose_name = "Categoría Permitida"
        verbose_name_plural = "Categorías Permitidas"

    def __str__(self):
        return f"{self.usuario.email} → {self.categoria.nombre}"

class VisitaUsuario(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    pagina_visitada = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.usuario} - {self.pagina_visitada} ({self.fecha_hora})"


class EstadisticaUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_visitas = models.PositiveIntegerField(default=0)
    primera_visita = models.DateTimeField(auto_now_add=True)
    ultima_visita = models.DateTimeField(auto_now=True)
    libros_leidos = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Estadísticas de {self.usuario}"