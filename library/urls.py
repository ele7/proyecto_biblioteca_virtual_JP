from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'library'

urlpatterns = [
    # ── Raíz → redirige al login ───────────────────────────────────────────
    path('', RedirectView.as_view(pattern_name='library:login', permanent=False)),

    # ── Autenticación ──────────────────────────────────────────────────────
    path('login/',             views.login_view,       name='login'),
    path('logout/',            views.logout_view,      name='logout_view'),
    path('cambiar-password/',  views.cambiar_password, name='cambiar_password'),
    path('olvido-password/',   views.olvido_password,  name='olvido_password'),

    # ── Dashboard ──────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Usuarios (solo ADMIN) ──────────────────────────────────────────────
    path('usuarios/',                     views.usuarios_listar,      name='usuarios_listar'),
    path('usuarios/crear/',               views.usuarios_crear,       name='usuarios_crear'),
    path('usuarios/editar/<int:pk>/',     views.usuarios_editar,      name='usuarios_editar'),
    path('usuarios/eliminar/<int:pk>/',   views.usuarios_eliminar,    name='usuarios_eliminar'),
    path('usuarios/carga-masiva/',        views.carga_masiva_usuarios,        name='usuarios_carga_masiva'),
    path('usuarios/carga-masiva/plantilla/', views.descargar_plantilla_usuarios, name='usuarios_plantilla'),

    # ── Categorías (solo ADMIN) ────────────────────────────────────────────
    path('categorias/',                   views.categorias_listar, name='categorias_listar'),
    path('categorias/crear/',             views.categorias_crear,  name='categorias_crear'),
    path('categorias/editar/<int:pk>/',   views.categorias_editar, name='categorias_editar'),

    # ── Libros (solo ADMIN) ────────────────────────────────────────────────
    path('libros/',                              views.listar_libros,            name='listar_libros'),
    path('libros/agregar/',                      views.agregar_libro,            name='agregar_libro'),
    path('libros/editar/<int:libro_id>/',        views.editar_libro,             name='editar_libro'),
    path('libros/eliminar/<int:libro_id>/',      views.eliminar_libro,           name='eliminar_libro'),
    path('libros/categoria/<int:categoria_id>/', views.libros_por_categoria,     name='admin_libros_por_categoria'),
    path('libros/carga-masiva/',                 views.carga_masiva_libros,      name='libros_carga_masiva'),
    path('libros/carga-masiva/plantilla/',       views.descargar_plantilla_libros, name='libros_plantilla'),

    # ── Libros (ADMIN y LECTOR) ────────────────────────────────────────────
    path('leer/<slug:autor_slug>/<slug:titulo_slug>/', views.leer_libro,             name='leer_libro'),
    path('buscar/',                           views.buscar_libro,                 name='buscar_libro'),
    path('categoria/<int:categoria_id>/',     views.libros_por_categoria_usuario, name='libros_por_categoria'),
    path('libro/<int:libro_id>/',             views.detalle_libro_usuario,        name='detalle_libros'),

    # ── Perfil y estadísticas (ADMIN y LECTOR) ─────────────────────────────
    path('perfil/',             views.user_profile,    name='user_profile'),
    path('perfil/stats-json/',  views.visit_stats_api, name='visit_stats_api'),

    # ── Estadísticas globales (solo ADMIN) ────────────────────────────────
    path('visitas/', views.visitas_usuarios, name='visitas_usuarios'),

    # ── Versículo del Día (ADMIN y LECTOR) ────────────────────────────────
    path('versiculo/', views.versiculo_diario, name='versiculo_diario'),

    # ── F2 Favoritos (ADMIN y LECTOR) ─────────────────────────────────────
    path('favoritos/',         views.mis_favoritos,   name='mis_favoritos'),
    path('favoritos/toggle/',  views.toggle_favorito, name='toggle_favorito'),

    # ── F3 Exportar Excel (solo ADMIN) ────────────────────────────────────
    path('exportar/usuarios/', views.exportar_usuarios_excel, name='exportar_usuarios_excel'),
    path('exportar/libros/',   views.exportar_libros_excel,   name='exportar_libros_excel'),

    # ── F5 Progreso de Lectura PDF (ADMIN y LECTOR) ────────────────────────
    path('progreso/guardar/', views.guardar_progreso, name='guardar_progreso'),
    path('progreso/',         views.obtener_progreso, name='obtener_progreso'),

    # ── F6 Solicitudes de Libros ──────────────────────────────────────────
    path('solicitudes/',                        views.solicitar_libro,           name='solicitar_libro'),
    path('panel/solicitudes/',                  views.panel_solicitudes,         name='panel_solicitudes'),
    path('panel/solicitudes/<int:pk>/estado/',  views.cambiar_estado_solicitud,  name='cambiar_estado_solicitud'),

    # ── F7 Auditoría (solo ADMIN) ─────────────────────────────────────────
    path('panel/auditoria/', views.auditoria_panel, name='auditoria_panel'),

    # ── Reflexiones (solo ADMIN) ──────────────────────────────────────────
    path('reflexiones/crear/',            views.crear_reflexion,    name='crear_reflexion'),
    path('reflexiones/<int:pk>/eliminar/', views.eliminar_reflexion, name='eliminar_reflexion'),
]
