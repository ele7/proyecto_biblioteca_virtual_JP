import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import Libro, ProgresoLectura
from ..permissions import usuario_puede_ver_libro


# ─────────────────────────────────────────────────────────────────────────────
# F5 — Progreso de Lectura PDF
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def guardar_progreso(request):
    """Guarda la última página leída. Llamado por AJAX desde el visor PDF."""
    try:
        data          = json.loads(request.body)
        libro_id      = int(data.get('libro_id', 0))
        ultima_pagina = max(1, int(data.get('ultima_pagina', 1)))
        total_paginas = max(1, int(data.get('total_paginas', 1)))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)

    libro = get_object_or_404(Libro, pk=libro_id)
    if not usuario_puede_ver_libro(request.user, libro):
        return JsonResponse({'error': 'Sin acceso.'}, status=403)

    progreso, _ = ProgresoLectura.objects.update_or_create(
        usuario=request.user,
        libro=libro,
        defaults={'ultima_pagina': ultima_pagina, 'total_paginas': total_paginas},
    )
    return JsonResponse({'ok': True, 'ultima_pagina': progreso.ultima_pagina})


@login_required
def obtener_progreso(request):
    """Retorna el progreso guardado de un libro para el usuario actual."""
    libro_id = request.GET.get('libro_id', '')
    try:
        libro_id = int(libro_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'libro_id inválido.'}, status=400)

    progreso = ProgresoLectura.objects.filter(
        usuario=request.user, libro_id=libro_id
    ).first()
    return JsonResponse({
        'ultima_pagina': progreso.ultima_pagina if progreso else 1,
        'total_paginas': progreso.total_paginas if progreso else 1,
    })
