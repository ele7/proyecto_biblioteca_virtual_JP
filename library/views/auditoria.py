import logging

from django.core.paginator import Paginator
from django.shortcuts import render

from ..models import AuditLog
from ..permissions import admin_required

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper compartido — usado por otros módulos de vistas
# ─────────────────────────────────────────────────────────────────────────────

def _registrar_auditoria(request, accion: str, modelo: str, objeto_str: str, detalles: str = ''):
    """Crea un AuditLog para acciones administrativas (CREAR/EDITAR/ELIMINAR)."""
    try:
        AuditLog.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            accion=accion,
            modelo_afectado=modelo,
            objeto_str=objeto_str[:255],
            detalles=detalles,
        )
    except Exception as exc:
        logger.warning("No se pudo registrar auditoría: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# F7 — Panel de Auditoría
# ─────────────────────────────────────────────────────────────────────────────

@admin_required
def auditoria_panel(request):
    logs = AuditLog.objects.select_related('usuario')

    accion = request.GET.get('accion', '').strip()
    modelo = request.GET.get('modelo', '').strip()
    if accion:
        logs = logs.filter(accion=accion)
    if modelo:
        logs = logs.filter(modelo_afectado=modelo)

    paginator = Paginator(logs, 30)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    modelos_disponibles = (
        AuditLog.objects.values_list('modelo_afectado', flat=True)
        .distinct().order_by('modelo_afectado')
    )
    return render(request, 'maestros/auditoria/panel.html', {
        'page_obj':             page_obj,
        'accion_filtro':        accion,
        'modelo_filtro':        modelo,
        'modelos_disponibles':  modelos_disponibles,
        'acciones_disponibles': ['CREAR', 'EDITAR', 'ELIMINAR'],
    })
