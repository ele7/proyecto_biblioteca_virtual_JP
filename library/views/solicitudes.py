from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import SolicitudLibroForm
from ..models import SolicitudLibro
from ..permissions import admin_required


# ─────────────────────────────────────────────────────────────────────────────
# F6 — Solicitudes de Libros
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def solicitar_libro(request):
    if request.method == 'POST':
        form = SolicitudLibroForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            solicitud.save()
            messages.success(request, "Solicitud enviada correctamente. El administrador la revisará pronto.")
            return redirect('library:solicitar_libro')
    else:
        form = SolicitudLibroForm()

    mis_solicitudes = (
        SolicitudLibro.objects
        .filter(usuario=request.user)
        .order_by('-fecha_creacion')[:10]
    )
    return render(request, 'maestros/solicitudes/crear.html', {
        'form':            form,
        'mis_solicitudes': mis_solicitudes,
    })


@admin_required
def panel_solicitudes(request):
    estado_filtro = request.GET.get('estado', '')
    solicitudes   = SolicitudLibro.objects.select_related('usuario')
    if estado_filtro:
        solicitudes = solicitudes.filter(estado=estado_filtro)
    solicitudes = solicitudes.order_by('-fecha_creacion')
    return render(request, 'maestros/solicitudes/panel.html', {
        'solicitudes':     solicitudes,
        'estado_filtro':   estado_filtro,
        'estados_choices': SolicitudLibro.ESTADOS,
    })


@admin_required
@require_POST
def cambiar_estado_solicitud(request, pk):
    solicitud      = get_object_or_404(SolicitudLibro, pk=pk)
    nuevo_estado   = request.POST.get('estado', '')
    estados_validos = [e[0] for e in SolicitudLibro.ESTADOS]
    if nuevo_estado in estados_validos:
        solicitud.estado = nuevo_estado
        solicitud.save(update_fields=['estado'])
        messages.success(request, f"Solicitud marcada como «{solicitud.get_estado_display()}».")
    else:
        messages.error(request, "Estado no válido.")
    return redirect('library:panel_solicitudes')
