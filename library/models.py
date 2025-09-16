from django.db import models
from django.contrib.auth.models import User


class Usuario(models.Model):
    username = models.CharField(max_length=150, unique=True)
    nombre = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.username
    
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre 

def renombrar_archivo(instance, filename):
    """
    Renombra el archivo para eliminar espacios y caracteres problemáticos.
    """
    # Obtener la extensión
    extension = filename.split('.')[-1]

    # Crear un nombre seguro basado en el título del libro
    nombre_limpio = instance.titulo.replace(' ', '_') # Convierte "Mi Libro (1)" -> "mi-libro-1"

    # Retornar la ruta completa
    return f'libros/{nombre_limpio}.{extension}'

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


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

class Perfil(models.Model):
    ROLES = (
        ('ADMIN', 'Administrador'),
        ('PROF', 'Profesor'),
        ('ALUM', 'Alumno'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=5, choices=ROLES)
    profesor_asignado = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='alumnos'
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_rol_display()}"


class Material(models.Model):
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    profesor = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.titulo


