from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
   
    path('dashboard/', views.dashboard, name='dashboard'),
    # Usuarios
    path('usuarios/', views.usuarios_listar, name='usuarios_listar'),
    path('usuarios/crear/', views.usuarios_crear, name='usuarios_crear'),
    path('usuarios/editar/<int:pk>/', views.usuarios_editar, name='usuarios_editar'),
    # Categorías
    path('categorias/', views.categorias_listar, name='categorias_listar'),
    path('categorias/crear/', views.categorias_crear, name='categorias_crear'),
    path('categorias/editar/<int:id>/', views.categorias_editar, name='categorias_editar'),
    path('leer/<int:libro_id>/', views.leer_libro, name='leer_libro'),
    path('agregar/', views.agregar_libro, name='agregar_libro'),
    path('editar/<int:libro_id>/', views.editar_libro, name='editar_libro'),
    path('categoria/<int:categoria_id>/', views.libros_por_categoria, name='libros_por_categoria'),
]
