from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from ..forms import ReflexionForm
from ..models import Reflexion
from ..permissions import es_admin


@login_required
@require_POST
def crear_reflexion(request):
    if not es_admin(request.user):
        return redirect('library:dashboard')

    form = ReflexionForm(request.POST)
    if form.is_valid():
        reflexion = form.save(commit=False)
        reflexion.creado_por = request.user
        reflexion.save()

    return redirect('library:dashboard')


@login_required
@require_POST
def eliminar_reflexion(request, pk):
    if not es_admin(request.user):
        return redirect('library:dashboard')

    reflexion = get_object_or_404(Reflexion, pk=pk)
    reflexion.delete()
    return redirect('library:dashboard')
