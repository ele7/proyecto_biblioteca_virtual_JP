import csv
import uuid
import re
from functools import wraps
from django.http import JsonResponse
import pandas as pd
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from .forms import CustomUserChangeForm, LibroForm, CategoriaForm, UploadUsersForm, UsuarioForm
from .models import CustomUser, EstadisticaUsuario, Libro , Categoria , CategoriaPermitida, Rol, VisitaUsuario
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required , user_passes_test
from library import models
from django.db.models import Q

User = get_user_model()

def login_view(request):
    email = ""
    # Limpiar mensajes previos
    list(messages.get_messages(request))

    if request.method == "POST":
        email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not email or not password:
            messages.error(request, "Debes ingresar email y contraseña")
        else:
            # Validación de formato de email
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Email no válido")
            else:
                # Autenticación usando email
                user = authenticate(request, email=email, password=password)
                if user:
                    login(request, user)
                    return redirect('library:dashboard')
                else:
                    messages.error(request, "Email o contraseña incorrecta")

    return render(request, "login.html", {"username": email})


def renombrar_archivo(instance, filename):
    # Tu versión original mejorada
    extension = filename.split('.')[-1]
    nombre_limpio = instance.titulo.replace(' ', '_')
    
    # Limpiar caracteres problemáticos
   
    nombre_limpio = re.sub(r'[^\w\-_]', '', nombre_limpio)
    
    # Agregar ID único para evitar sobreescritura
    
    unique_id = uuid.uuid4().hex[:6]
    
    return f'libros/{nombre_limpio}_{unique_id}.{extension}'

def rol_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'rol') or request.user.rol.nombre != 'ADMIN':
            return redirect('library:dashboard')  # Redirige a su panel
        return view_func(request, *args, **kwargs)
    return wrapper

@require_POST
def logout_view(request):
    logout(request)
    return redirect('library:login')

# 📌 LISTAR USUARIOS

@login_required
def usuarios_listar(request):
    usuarios = User.objects.all()
    
    usuarios_con_categorias = []
    for u in usuarios:
        cats = CategoriaPermitida.objects.filter(usuario=u).values_list('categoria__nombre', flat=True)
        usuarios_con_categorias.append({
        'usuario': u,
        'categorias': list(cats)
    })

    context = {
        "usuarios_con_categorias": usuarios_con_categorias
}
    return render(request, "maestros/usuarios/listar.html", context)

# 📌 CREAR USUARIO
@login_required
def usuarios_crear(request):
    categorias = Categoria.objects.all()
    categorias_usuario = [] 

    if request.method == "POST":
        form = UsuarioForm(request.POST)
        categorias_seleccionadas = request.POST.getlist('categorias')  

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
#
            for cat_id in categorias_seleccionadas:
                categoria_obj = Categoria.objects.get(id=cat_id)
                CategoriaPermitida.objects.create(usuario=user, categoria=categoria_obj)

            messages.success(request, "Usuario creado correctamente")
            return redirect("library:usuarios_listar")
    else:
        form = UsuarioForm()

    return render(
        request,
        "maestros/usuarios/crear.html",
        {
            "form": form,
            "categorias": categorias,
            "categorias_usuario": categorias_usuario,
        },
    )

# 📌 EDITAR USUARIO

@rol_admin_required
def usuarios_editar(request, pk):
    usuario = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=usuario)
        if form.is_valid():
            user = form.save(commit=False)
            messages.success(request, "Usuario actualizado correctamente")
            pwd = form.cleaned_data.get('password')
            if pwd:
                user.set_password(pwd)
            user.save()

            # Actualizar categorías
            categorias_seleccionadas = form.cleaned_data['categorias']
            # Borrar las que no están seleccionadas
            CategoriaPermitida.objects.filter(usuario=user).exclude(categoria__in=categorias_seleccionadas).delete()
            # Agregar las nuevas que no existían
            for cat in categorias_seleccionadas:
                CategoriaPermitida.objects.get_or_create(usuario=user, categoria=cat)

            
            return redirect("library:usuarios_listar")
    else:
        # Preseleccionar categorías actuales
        categorias_actuales = CategoriaPermitida.objects.filter(usuario=usuario).values_list('categoria', flat=True)
        form = CustomUserChangeForm(instance=usuario)
        form.fields['categorias'].initial = categorias_actuales

    return render(request, "maestros/usuarios/editar.html", {"form": form, "usuario": usuario})

# Crear categoría

@rol_admin_required
def categorias_crear(request):
    if request.method == "POST":
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("library:categorias_listar")
    else:
        form = CategoriaForm()
    return render(request, 'maestros/libros/crear.html', {'form': form})


# Editar categoría

@rol_admin_required
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

def categorias_listar(request):
    categorias = Categoria.objects.all()
    return render(request, 'maestros/libros/listar.html', {'categorias': categorias})


@login_required
def dashboard(request):
    usuario = request.user

    # Obtener IDs de categorías permitidas
    categorias_permitidas_ids = CategoriaPermitida.objects.filter(
        usuario=usuario
    ).values_list('categoria_id', flat=True)

    # Obtener categorías permitidas con prefetch
    categorias = Categoria.objects.filter(
        id__in=categorias_permitidas_ids
    ).prefetch_related('libros')

    categorias_data = []
    for categoria in categorias:
        libros_list = categoria.libros.all().order_by('titulo')
        
        paginator = Paginator(libros_list, 4)
        page_param = f'page_{categoria.id}'
        page_number = request.GET.get(page_param, 1)
        page_obj = paginator.get_page(page_number)

        categorias_data.append({
            'id': categoria.id,
            'nombre': categoria.nombre,
            'total_libros': libros_list.count(),
            'page_number': page_obj.number,
            'object_count': page_obj.object_list.count(),
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else 1,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else paginator.num_pages,
            'page_range': range(1, paginator.num_pages + 1),
            'libros': list(page_obj.object_list),
        })

    context = {'categorias': categorias_data}
    return render(request, "library/dashboard.html", context)


@rol_admin_required
def leer_libro(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    
    # Debug: Verificar si el template existe
    from django.template.loader import get_template
    try:
        template = get_template('maestros/libros/leer_libro.html')
        print("✅ Template encontrado")
    except Exception as e:
        print(f"❌ Error cargando template: {e}")
    
    print(f"🔍 DEBUG - Libro: {libro.titulo}, Archivo: {libro.archivo}")
    return render(request, 'maestros/libros/leer_libro.html', {'libro': libro})

@rol_admin_required
def listar_libros(request):
    libros = Libro.objects.all()  # Obtener todos los libros
    return render(request, 'maestros/libros/listar_libros.html', {'libros': libros})

@rol_admin_required
def agregar_libro(request):
    if request.method == "POST":
        form = LibroForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('library:listar_libros')
    else:
        form = LibroForm()
    return render(request, 'maestros/libros/agregar_libro.html', {'form': form})


@rol_admin_required
def libros_por_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    libros = Libro.objects.filter(categoria=categoria)
    return render(request, 'maestros/libros/libros_categoria.html', {
        'categoria': categoria,
        'libros': libros,
    })

@rol_admin_required
def editar_libro(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    if request.method == 'POST':
        form = LibroForm(request.POST, request.FILES, instance=libro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Libro actualizado correctamente.')
            return redirect('library:listar_libros')  
        else:
            messages.error(request, 'Error al actualizar el libro.')
    else:
        form = LibroForm(instance=libro)
    
    return render(request, 'maestros/libros/editar_libro.html', {'form': form, 'libro': libro})

User = get_user_model()

@user_passes_test(lambda u: u.is_superuser) # type: ignore
def visitas_usuarios(request):
    usuarios = User.objects.all()
    return render(request, "visitas_usuarios.html", {"usuarios": usuarios})

def libros_usuario(request):
    # Obtenemos las categorías permitidas para este usuario
    categorias = CategoriaPermitida.objects.filter(
        usuario=request.user
    ).values_list('categoria', flat=True)

    # Solo libros de esas categorías
    libros = Libro.objects.filter(categoria__in=categorias)

    return render(request, 'libros.html', {'libros': libros})

@rol_admin_required
def carga_masiva_usuarios(request):
    if request.method == "POST":
        form = UploadUsersForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES["archivo"]
            ext = archivo.name.split('.')[-1].lower()
            data_rows = []

            # Leer archivo según extensión
            if ext == "csv":
                decoded_file = archivo.read().decode("utf-8").splitlines()
                reader = csv.DictReader(decoded_file)
                data_rows = list(reader)
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(archivo)
                data_rows = df.to_dict(orient="records")
            else:
                messages.error(request, "Formato no soportado. Usa CSV o Excel.")
                return redirect("usuarios_carga_masiva")

            creados = 0
            omitidos = 0

            for row in data_rows:
                name = row.get("name", "").strip()
                email = row.get("email", "").strip()
                rol = row.get("rol", None)
                password = row.get("password", "123456")  # contraseña por defecto si no viene

                # Verificar duplicado por email
                if not email:
                    messages.warning(request, "Fila omitida: falta email.")
                    omitidos += 1
                    continue
                if User.objects.filter(email=email).exists():
                    messages.warning(request, f"Usuario con email '{email}' ya existe, se omite.")
                    omitidos += 1
                    continue

                rol_obj = None
                rol_nombre = row.get("rol", "").strip()
                if rol_nombre:
                    try:
                        rol_obj = Rol.objects.get(nombre=rol_nombre)  # o usa id si tu CSV tiene id
                    except Rol.DoesNotExist:
                        messages.warning(request, f"Fila omitida: rol '{rol_nombre}' no existe.")
                        omitidos += 1
                        continue
                else:
                    messages.warning(request, "Fila omitida: falta rol.")
                    omitidos += 1
                    continue

                # Crear usuario
                user = User.objects.create_user(
                    name=row.get("name", "").strip(),
                    email=row.get("email", "").strip(),
                    password=str(row.get("password", "123456")).strip(),
                    rol=rol_obj
                )

                # Asignar categorías
                categorias = [c.strip() for c in row.get("categorias", "").split(",") if c.strip()]
                for nombre in categorias:
                    categoria, _ = Categoria.objects.get_or_create(nombre=nombre)
                    CategoriaPermitida.objects.get_or_create(usuario=user, categoria=categoria)

                creados += 1

            messages.success(request, f"{creados} usuarios creados correctamente.")
            if omitidos:
                messages.warning(request, f"{omitidos} filas omitidas por duplicados o datos faltantes.")

            return redirect("library:usuarios_listar")
    else:
        form = UploadUsersForm()

    return render(request, "maestros/usuarios/carga_masiva.html", {"form": form})

@rol_admin_required

def user_profile(request):
    registrar_visita(request)  # 👈 registra cada entrada al perfil

    stats_obj = EstadisticaUsuario.objects.filter(usuario=request.user).first()
    stats = {
        'total_visits': stats_obj.total_visitas if stats_obj else 0,
        'first_visit': stats_obj.primera_visita if stats_obj else None,
        'last_visit': stats_obj.ultima_visita if stats_obj else None,
    }

    recent_visits = VisitaUsuario.objects.filter(usuario=request.user).order_by('-fecha_hora')[:5]

    context = {
        'user': request.user,
        'stats': stats,
        'recent_visits': recent_visits,
    }
    return render(request, 'user_profile.html', context)



@rol_admin_required
def visit_stats_api(request):
    """Devuelve estadísticas en JSON para actualizar en tiempo real"""
    stats_obj = EstadisticaUsuario.objects.filter(usuario=request.user).first()
    if not stats_obj:
        return JsonResponse({'error': 'No stats found'})

    data = {
        'total_visits': stats_obj.total_visitas,
        'first_visit': stats_obj.primera_visita.strftime('%d/%m/%Y') if stats_obj.primera_visita else None,
        'last_visit': stats_obj.ultima_visita.strftime('%d/%m/%Y') if stats_obj.ultima_visita else None,
    }
    return JsonResponse(data)

def registrar_visita(request):
    usuario = request.user
    ip = get_client_ip(request)

    # Actualizar estadísticas
    stats, created = EstadisticaUsuario.objects.get_or_create(usuario=usuario)
    stats.total_visitas += 1
    if not stats.primera_visita:
        stats.primera_visita = now()
    stats.ultima_visita = now()
    stats.save()

    # Registrar detalle
    VisitaUsuario.objects.create(
        usuario=usuario,
        fecha_hora=now(),
        ip_address=ip
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")

@login_required
def libros_por_categoria_usuario(request, categoria_id):
    """Página con todos los libros de una categoría específica"""
    categoria = get_object_or_404(Categoria, id=categoria_id)
    
    # Verificar si el usuario tiene acceso a esta categoría
    if not request.user.is_superuser:
        if not CategoriaPermitida.objects.filter(usuario=request.user, categoria=categoria).exists():
            messages.error(request, "No tienes acceso a esta categoría")
            return redirect('library:dashboard')
    
    # Obtener todos los libros de la categoría (sin paginación)
    libros = Libro.objects.filter(categoria=categoria).order_by('titulo')
    
    return render(request, 'library/categorias/libros_por_categoria.html', {
        'categoria': categoria,
        'libros': libros
    })

@login_required
def detalle_libro_usuario(request, libro_id):
    """Detalle de un libro específico"""
    libro = get_object_or_404(Libro, id=libro_id)
    
    # Verificar acceso a la categoría del libro
    if not request.user.is_superuser:
        if not CategoriaPermitida.objects.filter(
            usuario=request.user, 
            categoria=libro.categoria
        ).exists():
            messages.error(request, "No tienes acceso a este libro")
            return redirect('library:dashboard')
    
    return render(request, 'library/categorias/detalle_libro.html', {
        'libro': libro
    })


@login_required
def buscar_libro(request):
    """Vista para buscar libros"""
    query = request.GET.get('q', '').strip()
    libros = Libro.objects.none()
    
    if query:
        # Buscar por título o autor
        libros = Libro.objects.filter(
            Q(titulo__icontains=query) | 
            Q(autor__icontains=query)
        ).order_by('titulo')
        
        # Si el usuario no es superuser, filtrar por categorías permitidas
        if not request.user.is_superuser:
            categorias_permitidas = CategoriaPermitida.objects.filter(
                usuario=request.user
            ).values_list('categoria_id', flat=True)
            libros = libros.filter(categoria_id__in=categorias_permitidas)
    
    return render(request, 'library/buscar_libro.html', {
        'libros': libros,
        'query': query,
        'resultados_count': libros.count()
    })