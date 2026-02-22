from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from ..constants import RolNombre
from ..models import Categoria, CategoriaPermitida, Favorito, HistorialLectura, Libro
from ..permissions import es_admin

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    usuario = request.user
    usuario_es_admin = es_admin(usuario)

    if usuario_es_admin:
        categorias = Categoria.objects.all().prefetch_related('libros')
    else:
        categorias_ids = CategoriaPermitida.objects.filter(
            usuario=usuario
        ).values_list('categoria_id', flat=True)
        categorias = Categoria.objects.filter(
            id__in=categorias_ids
        ).prefetch_related('libros')

    categorias_data = []
    for categoria in categorias:
        libros_list = list(categoria.libros.all().order_by('titulo'))

        paginator   = Paginator(libros_list, 4)
        page_param  = f'page_{categoria.id}'
        page_number = request.GET.get(page_param, 1)
        page_obj    = paginator.get_page(page_number)

        categorias_data.append({
            'id':                   categoria.id,
            'nombre':               categoria.nombre,
            'total_libros':         len(libros_list),
            'page_number':          page_obj.number,
            'object_count':         len(page_obj.object_list),
            'total_pages':          paginator.num_pages,
            'has_previous':         page_obj.has_previous(),
            'has_next':             page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else 1,
            'next_page_number':     page_obj.next_page_number() if page_obj.has_next() else paginator.num_pages,
            'page_range':           range(1, paginator.num_pages + 1),
            'libros':               list(page_obj.object_list),
        })

    # ── Stats para ADMIN en el dashboard ──────────────────────────────────────
    stats_admin = None
    if usuario_es_admin:
        stats_admin = {
            'total_usuarios':   User.objects.count(),
            'total_lectores':   User.objects.filter(rol__nombre=RolNombre.LECTOR).count(),
            'total_libros':     Libro.objects.count(),
            'total_categorias': Categoria.objects.count(),
        }

    # ── Versículo del día (se cachea en memoria, no hace request extra) ────────
    versiculo = None
    try:
        from ..services.bible_api import get_pasaje_del_dia, obtener_versiculo
        passage_id = get_pasaje_del_dia()
        versiculo  = obtener_versiculo(passage_id)
    except Exception:
        pass  # Si falla la API, el dashboard igual funciona sin versículo

    # ── Historial reciente del usuario (últimos 4 libros abiertos) ─────────────
    historial_reciente = (
        HistorialLectura.objects
        .filter(usuario=usuario)
        .select_related('libro')
        .order_by('-fecha_apertura')[:4]
    )

    # ── Stats personales del usuario ──────────────────────────────────────────
    total_favoritos = Favorito.objects.filter(usuario=usuario).count()
    total_leidos    = HistorialLectura.objects.filter(usuario=usuario).values('libro').distinct().count()

    return render(request, "library/dashboard.html", {
        'categorias':        categorias_data,
        'stats_admin':       stats_admin,
        'versiculo':         versiculo,
        'historial_reciente': historial_reciente,
        'total_favoritos':   total_favoritos,
        'total_leidos':      total_leidos,
    })
