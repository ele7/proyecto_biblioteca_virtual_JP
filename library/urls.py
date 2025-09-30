from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout_view'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    
    # Usuarios
    path('usuarios/', views.usuarios_listar, name='usuarios_listar'),
    path('usuarios/crear/', views.usuarios_crear, name='usuarios_crear'),
    path('usuarios/editar/<int:pk>/', views.usuarios_editar, name='usuarios_editar'),
    path("usuarios/carga-masiva/", views.carga_masiva_usuarios, name="usuarios_carga_masiva"),

    # Categorías
    path('categorias/', views.categorias_listar, name='categorias_listar'),
    path('categorias/crear/', views.categorias_crear, name='categorias_crear'),
    path('categorias/editar/<int:pk>/', views.categorias_editar, name='categorias_editar'),
    path('categoria/<int:categoria_id>/', views.libros_por_categoria_usuario, name='libros_por_categoria'),
    path('libro/<int:libro_id>/', views.detalle_libro_usuario, name='detalle_libros'),
    # Libros
    path('buscar/', views.buscar_libro, name='buscar_libro'),
    path('leer/<int:libro_id>/', views.leer_libro, name='leer_libro'),
    path('libros/agregar/', views.agregar_libro, name='agregar_libro'),
    path('libros/editar/<int:libro_id>/', views.editar_libro, name='editar_libro'),
    path('libros/', views.listar_libros, name='listar_libros'),
    path('categoria/<int:categoria_id>/', views.libros_por_categoria, name='libros_por_categoria'),
    path("visitas/", views.visitas_usuarios, name="visitas_usuarios"),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/stats-json/', views.visit_stats_api, name='visit_stats_api'),
]

