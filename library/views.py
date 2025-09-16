from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import LibroForm, CategoriaForm
from .models import Libro , Categoria, Usuario
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
import json
from django.views.decorators.csrf import csrf_exempt




def login_view(request):
    if request.method == "GET":
        # Renderiza el formulario
        return render(request, "login.html")

    elif request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({"success": True, "redirect": "/dashboard/"})
        else:
            return JsonResponse({"success": False, "error": "Credenciales inválidas"})

    return JsonResponse({"error": "Método no permitido"}, status=405)


def logout_view(request):
    logout(request)
    return redirect("login")


# 📌 LISTAR USUARIOS

@login_required
def usuarios_listar(request):
    usuarios = User.objects.all()
    return render(request, "maestros/usuarios/listar.html", {"usuarios": usuarios})

# 📌 CREAR USUARIO

@login_required
def usuarios_crear(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "El usuario ya existe")
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Usuario creado correctamente")
            return redirect("usuarios_listar")

    return render(request, "maestros/usuarios/crear.html")

# 📌 EDITAR USUARIO

@login_required
def usuarios_editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        usuario.username = request.POST.get("username")
        usuario.email = request.POST.get("email")
        password = request.POST.get("password")

        if password:
            usuario.set_password(password)

        usuario.save()
        messages.success(request, "Usuario actualizado correctamente")
        return redirect("usuarios_listar")

    return render(request, "maestros/usuarios/editar.html", {"usuario": usuario})

# Listar categorías

@login_required
def categorias_listar(request):
    categorias = Categoria.objects.all()
    return render(request, "maestros/libros/listar.html", {"categorias": categorias})

# Crear categoría

@login_required
def categorias_crear(request):
    if request.method == "POST":
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("categorias_listar")
    else:
        form = CategoriaForm()
    return render(request, "maestros/libros/crear.html", {"form": form})

# Editar categoría

@login_required
def categorias_editar(request, id):
    categoria = get_object_or_404(Categoria, pk=id)

    if request.method == "POST":
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect('categorias_listar')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'maestros/libros/editar.html', {
        'form': form,
        'categoria': categoria  # Esto es para tu template
    })

@login_required
def dashboard(request):
    categorias = Categoria.objects.all().prefetch_related("libros")
    return render(request, 'library/dashboard.html', {
        'categorias': categorias
    })


@login_required
def leer_libro(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    return render(request, 'library/leer_libro.html', {'libro': libro})


@login_required
def agregar_libro(request):
    if request.method == "POST":
        form = LibroForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('dashboard') 
    else:
        form = LibroForm()
    return render(request, 'library/agregar_libro.html', {'form': form})


@login_required
def libros_por_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    libros = Libro.objects.filter(categoria=categoria)
    return render(request, 'library/libros_categoria.html', {
        'categoria': categoria,
        'libros': libros,
    })


@login_required
def editar_libro(request, libro_id):
    libro = get_object_or_404(Libro, pk=libro_id)

    if request.method == "POST":
        form = LibroForm(request.POST, request.FILES, instance=libro)
        if form.is_valid():
            if 'archivo' in request.FILES:
                libro.archivo = request.FILES['archivo']
            form.save()
            messages.success(request, "Se editaron los cambios correctamente.")
            return redirect('editar_libro', libro_id=libro.id)
        else:
            print("❌ Errores del formulario:", form.errors)  # 👈 DEPURACIÓN
            messages.error(request, "Hubo un error al editar el libro.")
    else:
        form = LibroForm(instance=libro)

    return render(request, 'library/editar_libro.html', {'form': form, 'libro': libro})
