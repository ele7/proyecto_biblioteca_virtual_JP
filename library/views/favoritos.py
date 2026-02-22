import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ..models import Favorito, Libro
from ..permissions import usuario_puede_ver_libro


# ─────────────────────────────────────────────────────────────────────────────
# F2 — Favoritos
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_favorito(request):
    """Toggle de favorito vía AJAX (JSON). Devuelve {'is_favorito': bool}."""
    try:
        data     = json.loads(request.body)
        libro_id = int(data.get('libro_id', 0))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Datos inválidos.'}, status=400)

    libro = get_object_or_404(Libro, pk=libro_id)
    if not usuario_puede_ver_libro(request.user, libro):
        return JsonResponse({'error': 'Sin acceso a este libro.'}, status=403)

    fav, created = Favorito.objects.get_or_create(usuario=request.user, libro=libro)
    if not created:
        fav.delete()
        is_favorito = False
    else:
        is_favorito = True

    return JsonResponse({'is_favorito': is_favorito})


@login_required
def mis_favoritos(request):
    favoritos = (
        Favorito.objects
        .filter(usuario=request.user)
        .select_related('libro__categoria')
        .order_by('-fecha_agregado')
    )
    return render(request, 'library/mis_favoritos.html', {'favoritos': favoritos})
