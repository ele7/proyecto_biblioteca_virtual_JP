from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings

from .constants import RolNombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


def renombrar_archivo(instance, filename):
    import re
    import uuid
    extension = filename.split('.')[-1]
    nombre_limpio = re.sub(r'[^\w\-_]', '', instance.titulo.replace(' ', '_'))
    unique_id = uuid.uuid4().hex[:6]
    return f'libros/{nombre_limpio}_{unique_id}.{extension}'


class Libro(models.Model):
    titulo      = models.CharField(max_length=200)
    autor       = models.CharField(max_length=200)
    isbn        = models.CharField(max_length=20, blank=True, null=True, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    categoria   = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="libros")
    portada     = models.ImageField(upload_to="portadas/", blank=True, null=True)
    archivo     = models.FileField(upload_to=renombrar_archivo, blank=True, null=True)
    año         = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.titulo} - {self.autor}"


class Rol(models.Model):
    nombre = models.CharField(
        max_length=50,
        unique=True,
        choices=RolNombre.CHOICES,
    )

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
        # Garantiza que el rol ADMIN exista en la BD
        rol_admin, _ = Rol.objects.get_or_create(nombre=RolNombre.ADMIN)
        extra_fields.setdefault('rol', rol_admin)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    name  = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    rol   = models.ForeignKey(Rol, on_delete=models.CASCADE)
    categorias = models.ManyToManyField(
        Categoria,
        through="CategoriaPermitida",
        blank=True,
        related_name="usuarios",
    )
    is_active             = models.BooleanField(default=True)
    is_staff              = models.BooleanField(default=False)
    debe_cambiar_password = models.BooleanField(
        default=False,
        help_text="Si es True, el usuario deberá cambiar su contraseña al iniciar sesión.",
    )

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    # ── Propiedades de conveniencia ──────────────────────────────────────────

    @property
    def is_admin(self) -> bool:
        """True si el usuario tiene rol ADMIN."""
        if not self.rol_id:
            return False
        return self.rol.nombre == RolNombre.ADMIN

    @property
    def is_lector(self) -> bool:
        """True si el usuario tiene rol LECTOR."""
        if not self.rol_id:
            return False
        return self.rol.nombre == RolNombre.LECTOR

    def __str__(self):
        return f"{self.email} - {self.rol.nombre if self.rol_id else 'Sin rol'}"


class Material(models.Model):
    titulo    = models.CharField(max_length=200)
    contenido = models.TextField()
    profesor  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo


class CategoriaPermitida(models.Model):
    usuario   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        unique_together     = ('usuario', 'categoria')
        verbose_name        = "Categoría Permitida"
        verbose_name_plural = "Categorías Permitidas"

    def __str__(self):
        return f"{self.usuario.email} → {self.categoria.nombre}"


class VisitaUsuario(models.Model):
    usuario         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_hora      = models.DateTimeField(auto_now_add=True)
    ip_address      = models.GenericIPAddressField()
    pagina_visitada = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.usuario} - {self.pagina_visitada} ({self.fecha_hora})"


class EstadisticaUsuario(models.Model):
    usuario        = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_visitas  = models.PositiveIntegerField(default=0)
    primera_visita = models.DateTimeField(auto_now_add=True)
    ultima_visita  = models.DateTimeField(auto_now=True)
    libros_leidos  = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Estadísticas de {self.usuario}"


# ─────────────────────────────────────────────────────────────────────────────
# Nuevos modelos — F1 Historial, F2 Favoritos, F5 Progreso,
#                  F6 Solicitudes, F7 Auditoría
# ─────────────────────────────────────────────────────────────────────────────

class HistorialLectura(models.Model):
    """F1 — Registra cada apertura de un libro por un usuario."""
    usuario        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='historial_lectura',
    )
    libro          = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
        related_name='historial_lecturas',
    )
    fecha_apertura = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-fecha_apertura']
        verbose_name        = 'Historial de Lectura'
        verbose_name_plural = 'Historiales de Lectura'

    def __str__(self):
        return f"{self.usuario.email} → {self.libro.titulo} ({self.fecha_apertura:%d/%m/%Y})"


class Favorito(models.Model):
    """F2 — Libro marcado como favorito por un usuario."""
    usuario        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favoritos',
    )
    libro          = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
        related_name='favoritos',
    )
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together     = ('usuario', 'libro')
        ordering            = ['-fecha_agregado']
        verbose_name        = 'Favorito'
        verbose_name_plural = 'Favoritos'

    def __str__(self):
        return f"{self.usuario.email} ♥ {self.libro.titulo}"


class ProgresoLectura(models.Model):
    """F5 — Guarda la última página leída por usuario y libro."""
    usuario       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progresos_lectura',
    )
    libro         = models.ForeignKey(
        Libro,
        on_delete=models.CASCADE,
        related_name='progresos_lectura',
    )
    ultima_pagina = models.PositiveIntegerField(default=1)
    total_paginas = models.PositiveIntegerField(default=1)
    actualizado   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together     = ('usuario', 'libro')
        verbose_name        = 'Progreso de Lectura'
        verbose_name_plural = 'Progresos de Lectura'

    def __str__(self):
        return (
            f"{self.usuario.email} — {self.libro.titulo}: "
            f"p.{self.ultima_pagina}/{self.total_paginas}"
        )


class SolicitudLibro(models.Model):
    """F6 — Solicitud de un lector para agregar un libro a la biblioteca."""
    PENDIENTE = 'PENDIENTE'
    VISTA     = 'VISTA'
    ACEPTADA  = 'ACEPTADA'
    RECHAZADA = 'RECHAZADA'
    ESTADOS   = [
        (PENDIENTE, 'Pendiente'),
        (VISTA,     'Vista'),
        (ACEPTADA,  'Aceptada'),
        (RECHAZADA, 'Rechazada'),
    ]

    usuario         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solicitudes_libros',
    )
    titulo_sugerido = models.CharField(max_length=200)
    autor_sugerido  = models.CharField(max_length=200, blank=True, null=True)
    nota            = models.TextField(blank=True, null=True)
    estado          = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-fecha_creacion']
        verbose_name        = 'Solicitud de Libro'
        verbose_name_plural = 'Solicitudes de Libros'

    def __str__(self):
        return f"'{self.titulo_sugerido}' por {self.usuario.email} [{self.estado}]"


class AuditLog(models.Model):
    """F7 — Registro de acciones administrativas (crear/editar/eliminar)."""
    usuario         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    accion          = models.CharField(max_length=50)    # 'CREAR' | 'EDITAR' | 'ELIMINAR'
    modelo_afectado = models.CharField(max_length=100)   # 'Libro' | 'CustomUser' | 'Categoria'
    objeto_str      = models.CharField(max_length=255)
    detalles        = models.TextField(blank=True, null=True)
    fecha           = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-fecha']
        verbose_name        = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'

    def __str__(self):
        return f"[{self.fecha:%d/%m/%Y %H:%M}] {self.accion} {self.modelo_afectado}: {self.objeto_str}"
