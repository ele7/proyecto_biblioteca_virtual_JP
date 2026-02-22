import secrets
import string

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from library.forms import CambioPasswordForm, OlvidoPasswordForm


# ─────────────────────────────────────────────────────────────────────────────
# URL de cambio de contraseña obligatorio — excluida del redirect loop
# ─────────────────────────────────────────────────────────────────────────────
_CAMBIO_PWD_URL = 'library:cambiar_password'


def login_view(request):
    # Si ya está autenticado y debe cambiar password, redirigir
    if request.user.is_authenticated:
        if request.user.debe_cambiar_password:
            return redirect(_CAMBIO_PWD_URL)
        return redirect('library:dashboard')

    email = ""
    list(messages.get_messages(request))  # Limpiar mensajes previos

    if request.method == "POST":
        email    = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not email or not password:
            messages.error(request, "Debes ingresar email y contraseña.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "El formato del email no es válido.")
            else:
                user = authenticate(request, email=email, password=password)
                if user:
                    login(request, user)
                    # Redirigir a cambio obligatorio si aplica
                    if user.debe_cambiar_password:
                        messages.warning(
                            request,
                            "Por seguridad, debes cambiar tu contraseña antes de continuar.",
                        )
                        return redirect(_CAMBIO_PWD_URL)
                    return redirect('library:dashboard')
                else:
                    messages.error(request, "Email o contraseña incorrectos.")

    return render(request, "login.html", {"username": email})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('library:login')


# ─────────────────────────────────────────────────────────────────────────────
# Cambio de contraseña self-service (desde perfil o forzado al iniciar sesión)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def cambiar_password(request):
    """
    Permite al usuario cambiar su propia contraseña.
    Si `debe_cambiar_password` es True, es un cambio obligatorio.
    """
    es_obligatorio = request.user.debe_cambiar_password
    form = CambioPasswordForm()

    if request.method == "POST":
        form = CambioPasswordForm(request.POST)
        if form.is_valid():
            password_actual = form.cleaned_data['password_actual']
            password_nuevo  = form.cleaned_data['password_nuevo']

            # Verificar contraseña actual
            user = authenticate(request, email=request.user.email, password=password_actual)
            if user is None:
                form.add_error('password_actual', "La contraseña actual es incorrecta.")
            else:
                user.set_password(password_nuevo)
                user.debe_cambiar_password = False
                user.save()
                # Mantener la sesión activa después del cambio
                update_session_auth_hash(request, user)
                messages.success(request, "Contraseña actualizada correctamente.")
                return redirect('library:dashboard')

    context = {
        'form':          form,
        'es_obligatorio': es_obligatorio,
    }
    return render(request, "cambiar_password.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Olvidé mi contraseña — genera una temporal y envía email
# ─────────────────────────────────────────────────────────────────────────────

def olvido_password(request):
    """
    Si el email existe, genera una contraseña temporal, la asigna y envía
    un correo con las instrucciones. Siempre muestra el mismo mensaje para
    no revelar qué emails existen en el sistema.
    """
    form = OlvidoPasswordForm()

    if request.method == "POST":
        form = OlvidoPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            _procesar_olvido_password(email)
            messages.success(
                request,
                "Si el correo está registrado, recibirás una contraseña temporal en tu bandeja de entrada.",
            )
            return redirect('library:login')

    return render(request, "olvido_password.html", {"form": form})


def _procesar_olvido_password(email: str) -> None:
    """Genera contraseña temporal y envía email si el usuario existe."""
    from library.models import CustomUser
    from library.services.email_service import enviar_notificacion_password

    try:
        user = CustomUser.objects.get(email=email, is_active=True)
    except CustomUser.DoesNotExist:
        return  # No revelar si el email existe

    # Generar contraseña temporal de 10 caracteres
    alfabeto = string.ascii_letters + string.digits
    pwd_temporal = ''.join(secrets.choice(alfabeto) for _ in range(10))

    user.set_password(pwd_temporal)
    user.debe_cambiar_password = True
    user.save()

    enviar_notificacion_password(user, nueva_password=pwd_temporal)
