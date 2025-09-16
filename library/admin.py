from django.contrib import admin
from .models import Categoria, Libro

# Register your models here.
from django.contrib import admin
from .models import Categoria, Libro

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")

@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "autor", "categoria")
    list_filter = ("categoria",)
    search_fields = ("titulo", "autor")