from django.shortcuts import get_object_or_404, redirect, render

from ..forms import CategoriaForm
from ..models import Categoria
from ..permissions import admin_required
from .auditoria import _registrar_auditoria


# ─────────────────────────────────────────────────────────────────────────────
# Categorías — solo ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin_required
def categorias_listar(request):
    categorias = Categoria.objects.all()
    return render(request, 'maestros/libros/listar.html', {'categorias': categorias})


@admin_required
def categorias_crear(request):
    if request.method == "POST":
        form = CategoriaForm(request.POST)
        if form.is_valid():
            cat = form.save()
            _registrar_auditoria(request, 'CREAR', 'Categoria', str(cat))
            return redirect("library:categorias_listar")
    else:
        form = CategoriaForm()
    return render(request, 'maestros/libros/crear.html', {'form': form})


@admin_required
def categorias_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method == "POST":
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            cat = form.save()
            _registrar_auditoria(request, 'EDITAR', 'Categoria', str(cat))
            return redirect('library:categorias_listar')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'maestros/libros/editar.html', {
        'form':      form,
        'categoria': categoria,
    })
