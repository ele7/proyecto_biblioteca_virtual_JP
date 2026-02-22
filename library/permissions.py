"""
Sistema de permisos centralizado de la Biblioteca Virtual.

Toda la lógica de autorización vive aquí.
El resto del código importa desde este módulo; nunca verifica roles directamente.

Roles disponibles (ver constants.RolNombre):
    - ADMIN:  Acceso total al sistema.
    - LECTOR: Solo puede ver libros de sus categorías asignadas.
"""

import logging
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .constants import RolNombre

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Funciones de verificación — puras, sin side effects, fáciles de testear
# ─────────────────────────────────────────────────────────────────────────────

def es_admin(user) -> bool:
    """
    Retorna True si el usuario tiene rol ADMIN.

    Es la única fuente de verdad para esta verificación.
    No usa is_superuser; el rol en la base de datos manda.
    """
    if not user or not user.is_authenticated:
        return False
    rol = getattr(user, 'rol', None)
    return rol is not None and rol.nombre == RolNombre.ADMIN


def usuario_puede_ver_categoria(user, categoria_id: int) -> bool:
    """
    Retorna True si el usuario tiene acceso a la categoría dada.

    - ADMIN:  acceso a todas las categorías.
    - LECTOR: solo a las que tiene asignadas en CategoriaPermitida.
    """
    if es_admin(user):
        return True
    # Import lazy para evitar importación circular con models.py
    from .models import CategoriaPermitida
    return CategoriaPermitida.objects.filter(
        usuario_id=user.pk,
        categoria_id=categoria_id,
    ).exists()


def usuario_puede_ver_libro(user, libro) -> bool:
    """
    Retorna True si el usuario tiene acceso al libro dado.
    El acceso se hereda de la categoría del libro.
    """
    return usuario_puede_ver_categoria(user, libro.categoria_id)


# ─────────────────────────────────────────────────────────────────────────────
# Decoradores para vistas basadas en funciones (FBV)
# ─────────────────────────────────────────────────────────────────────────────

def admin_required(view_func):
    """
    Requiere que el usuario tenga rol ADMIN.

    Comportamiento:
        - No autenticado → redirige a library:login
        - LECTOR         → redirige a library:dashboard con mensaje de error
        - ADMIN          → ejecuta la vista normalmente

    Uso:
        @admin_required
        def mi_vista(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('library:login')
        if not es_admin(request.user):
            logger.warning(
                "Acceso denegado: usuario '%s' intentó acceder a '%s'",
                request.user.email,
                request.path,
            )
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect('library:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Mixins para vistas basadas en clases (CBV)
# ─────────────────────────────────────────────────────────────────────────────

class AdminRequiredMixin:
    """
    Requiere rol ADMIN. Para vistas basadas en clases.

    Uso:
        class MiVista(AdminRequiredMixin, View):
            ...
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('library:login')
        if not es_admin(request.user):
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect('library:dashboard')
        return super().dispatch(request, *args, **kwargs)


class LoginRequiredMixin:
    """
    Requiere autenticación (ADMIN o LECTOR). Para vistas basadas en clases.

    Uso:
        class MiVista(LoginRequiredMixin, View):
            ...
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('library:login')
        return super().dispatch(request, *args, **kwargs)
