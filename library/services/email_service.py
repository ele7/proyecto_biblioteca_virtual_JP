"""
services/email_service.py
──────────────────────────
Envío de correos transaccionales de la Biblioteca Virtual.

Funciones disponibles:
    enviar_bienvenida(user, password_plain)
        → Bienvenida con credenciales al usuario recién creado.

    enviar_notificacion_password(user, nueva_password=None)
        → Aviso de cambio de contraseña al usuario afectado.

    enviar_notificacion_libro(libro)
        → Notificación a usuarios con acceso a la categoría del libro.

Todas las funciones capturan excepciones internamente para que un
fallo de correo nunca interrumpa el flujo principal de la aplicación.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000')


# ─────────────────────────────────────────────────────────────────────────────
# Bienvenida — se envía al crear un usuario
# ─────────────────────────────────────────────────────────────────────────────

def enviar_bienvenida(user, password_plain: str) -> None:
    """
    Envía un correo de bienvenida con las credenciales de acceso.

    Args:
        user:           Instancia de CustomUser recién creado.
        password_plain: Contraseña en texto plano (antes de hashear).
    """
    context = {
        'nombre':        user.name or user.email,
        'email':         user.email,
        'password':      password_plain,
        'login_url':     f"{SITE_URL}/login/",
        'site_url':      SITE_URL,
    }
    _enviar(
        destinatario=user.email,
        asunto='Bienvenido a la Biblioteca Virtual — Tus credenciales de acceso',
        template_html='emails/bienvenida.html',
        context=context,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cambio de contraseña — se envía cuando un admin actualiza la contraseña
# ─────────────────────────────────────────────────────────────────────────────

def enviar_notificacion_password(user, nueva_password: str | None = None) -> None:
    """
    Notifica al usuario que su contraseña fue cambiada.

    Args:
        user:            Instancia de CustomUser afectado.
        nueva_password:  Nueva contraseña en texto plano (opcional).
                         Si se provee, se incluye en el correo.
    """
    context = {
        'nombre':         user.name or user.email,
        'email':          user.email,
        'nueva_password': nueva_password,
        'login_url':      f"{SITE_URL}/login/",
        'site_url':       SITE_URL,
    }
    _enviar(
        destinatario=user.email,
        asunto='Biblioteca Virtual — Tu contraseña ha sido actualizada',
        template_html='emails/cambio_password.html',
        context=context,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Nuevo libro — se envía a usuarios con acceso a la categoría del libro
# ─────────────────────────────────────────────────────────────────────────────

def enviar_notificacion_libro(libro) -> None:
    """
    Notifica a todos los usuarios activos con acceso a la categoría del libro.

    Consulta: CustomUser con CategoriaPermitida → categoria == libro.categoria.

    Args:
        libro: Instancia de Libro recién creado.
    """
    from library.models import CustomUser  # import local para evitar circular

    destinatarios = list(
        CustomUser.objects.filter(
            categoriapermitida__categoria=libro.categoria,
            is_active=True,
        )
        .distinct()
        .values_list('email', 'name')
    )

    if not destinatarios:
        logger.debug(
            "Nuevo libro '%s': no hay usuarios con acceso a la categoría '%s'.",
            libro.titulo, libro.categoria,
        )
        return

    libro_url = f"{SITE_URL}/libro/{libro.id}/"

    for email, nombre in destinatarios:
        context = {
            'nombre':     nombre or email,
            'titulo':     libro.titulo,
            'autor':      libro.autor,
            'año':        libro.año,
            'categoria':  libro.categoria.nombre,
            'descripcion': libro.descripcion or '',
            'libro_url':  libro_url,
            'site_url':   SITE_URL,
        }
        _enviar(
            destinatario=email,
            asunto=f'Nuevo libro disponible — {libro.titulo}',
            template_html='emails/nuevo_libro.html',
            context=context,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helper interno
# ─────────────────────────────────────────────────────────────────────────────

def _enviar(destinatario: str, asunto: str, template_html: str, context: dict) -> None:
    """
    Renderiza el template HTML, genera texto plano y envía el correo.
    Captura y registra cualquier excepción sin propagarla.
    """
    try:
        html_body  = render_to_string(template_html, context)
        text_body  = _html_a_texto(context)

        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)

        logger.info("Email '%s' enviado a %s", asunto, destinatario)

    except Exception as exc:
        logger.error(
            "Error enviando email '%s' a %s: %s",
            asunto, destinatario, exc,
        )


def _html_a_texto(context: dict) -> str:
    """Genera un texto plano genérico a partir del contexto del email."""
    lineas = [
        "Biblioteca Virtual — Pozo de Jacob",
        "─" * 40,
    ]
    for clave, valor in context.items():
        if clave in ('site_url',):
            continue
        if valor:
            lineas.append(f"{clave.replace('_', ' ').capitalize()}: {valor}")
    lineas.append("─" * 40)
    lineas.append(f"Accede en: {context.get('site_url', '')}")
    return "\n".join(lineas)
