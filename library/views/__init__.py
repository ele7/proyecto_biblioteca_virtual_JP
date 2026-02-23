# Re-exporta todas las vistas para mantener compatibilidad con urls.py
# que hace: from . import views  →  views.nombre_vista

from .auth import login_view, logout_view, cambiar_password, olvido_password
from .dashboard import dashboard
from .usuarios import (
    usuarios_listar,
    usuarios_crear,
    usuarios_editar,
    carga_masiva_usuarios,
    descargar_plantilla_usuarios,
)
from .categorias import categorias_listar, categorias_crear, categorias_editar
from .libros import (
    listar_libros,
    agregar_libro,
    editar_libro,
    libros_por_categoria,
    carga_masiva_libros,
    descargar_plantilla_libros,
    leer_libro,
    libros_usuario,
    libros_por_categoria_usuario,
    detalle_libro_usuario,
    buscar_libro,
)
from .favoritos import toggle_favorito, mis_favoritos
from .progreso import guardar_progreso, obtener_progreso
from .estadisticas import user_profile, visit_stats_api, visitas_usuarios
from .solicitudes import solicitar_libro, panel_solicitudes, cambiar_estado_solicitud
from .exportacion import exportar_usuarios_excel, exportar_libros_excel
from .versiculo import versiculo_diario
from .auditoria import auditoria_panel
from .media import servir_pdf_protegido, servir_portada_protegida
from .reflexiones import crear_reflexion, eliminar_reflexion

__all__ = [
    'login_view', 'logout_view', 'cambiar_password', 'olvido_password',
    'dashboard',
    'usuarios_listar', 'usuarios_crear', 'usuarios_editar',
    'carga_masiva_usuarios', 'descargar_plantilla_usuarios',
    'categorias_listar', 'categorias_crear', 'categorias_editar',
    'listar_libros', 'agregar_libro', 'editar_libro', 'libros_por_categoria',
    'carga_masiva_libros', 'descargar_plantilla_libros',
    'leer_libro', 'libros_usuario', 'libros_por_categoria_usuario',
    'detalle_libro_usuario', 'buscar_libro',
    'toggle_favorito', 'mis_favoritos',
    'guardar_progreso', 'obtener_progreso',
    'user_profile', 'visit_stats_api', 'visitas_usuarios',
    'solicitar_libro', 'panel_solicitudes', 'cambiar_estado_solicitud',
    'exportar_usuarios_excel', 'exportar_libros_excel',
    'versiculo_diario',
    'auditoria_panel',
    'servir_pdf_protegido',
    'servir_portada_protegida',
    'crear_reflexion',
    'eliminar_reflexion',
]
