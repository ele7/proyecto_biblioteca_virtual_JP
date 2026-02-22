from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render

from ..models import EstadisticaUsuario, Favorito, HistorialLectura, VisitaUsuario
from ..permissions import admin_required

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Perfil y estadísticas — ADMIN y LECTOR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def user_profile(request):
    stats_obj = EstadisticaUsuario.objects.filter(usuario=request.user).first()
    stats = {
        'total_visits': stats_obj.total_visitas if stats_obj else 0,
        'first_visit':  stats_obj.primera_visita if stats_obj else None,
        'last_visit':   stats_obj.ultima_visita if stats_obj else None,
    }
    recent_visits = VisitaUsuario.objects.filter(
        usuario=request.user
    ).order_by('-fecha_hora')[:5]

    # F1 — Historial de lectura reciente
    historial_reciente = (
        HistorialLectura.objects
        .filter(usuario=request.user)
        .select_related('libro__categoria')
        .order_by('-fecha_apertura')[:10]
    )
    libros_distintos_leidos = (
        HistorialLectura.objects
        .filter(usuario=request.user)
        .values('libro').distinct().count()
    )

    # F2 — Favoritos
    total_favoritos = Favorito.objects.filter(usuario=request.user).count()

    return render(request, 'user_profile.html', {
        'user':                    request.user,
        'stats':                   stats,
        'recent_visits':           recent_visits,
        'historial_reciente':      historial_reciente,
        'libros_distintos_leidos': libros_distintos_leidos,
        'total_favoritos':         total_favoritos,
    })


@login_required
def visit_stats_api(request):
    stats_obj = EstadisticaUsuario.objects.filter(usuario=request.user).first()
    if not stats_obj:
        return JsonResponse({'error': 'Sin estadísticas disponibles.'}, status=404)

    return JsonResponse({
        'total_visits': stats_obj.total_visitas,
        'first_visit':  stats_obj.primera_visita.strftime('%d/%m/%Y') if stats_obj.primera_visita else None,
        'last_visit':   stats_obj.ultima_visita.strftime('%d/%m/%Y') if stats_obj.ultima_visita else None,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Estadísticas globales — solo ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin_required
def visitas_usuarios(request):
    usuarios = User.objects.select_related('rol').all()

    # F8 — Insights globales
    libro_mas_leido = (
        HistorialLectura.objects
        .values('libro__id', 'libro__titulo', 'libro__autor')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )
    categoria_popular = (
        HistorialLectura.objects
        .values('libro__categoria__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )
    usuarios_activos = (
        EstadisticaUsuario.objects
        .select_related('usuario__rol')
        .order_by('-total_visitas')[:5]
    )

    return render(request, "visitas_usuarios.html", {
        "usuarios":          usuarios,
        "libro_mas_leido":   libro_mas_leido,
        "categoria_popular": categoria_popular,
        "usuarios_activos":  usuarios_activos,
    })
