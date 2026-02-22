import mimetypes

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404

from ..models import Libro
from ..permissions import usuario_puede_ver_libro


# ─────────────────────────────────────────────────────────────────────────────
# Servicio protegido de archivos media
#
# En DESARROLLO: Django sirve el archivo directamente con FileResponse.
# En PRODUCCIÓN: Django responde con X-Accel-Redirect y Nginx sirve el archivo
#                desde una ubicación interna (/protected-media/), sin cargarlo
#                en memoria Python.
#
# Configuración Nginx de producción necesaria:
#
#   location /protected-media/ {
#       internal;
#       alias /ruta/al/proyecto/media/;
#   }
#
#   location /media/ {
#       # No servir directamente — dejar que Django maneje la autenticación
#       return 404;
#   }
# ─────────────────────────────────────────────────────────────────────────────


def _get_libro_o_404(campo, ruta):
    """Busca el Libro cuyo campo (archivo/portada) coincide con la ruta dada."""
    libro = Libro.objects.filter(**{campo: ruta}).first()
    if not libro:
        raise Http404("Archivo no encontrado.")
    return libro


def _servir_archivo(libro_field, content_type):
    """
    Devuelve un FileResponse en desarrollo o una respuesta X-Accel-Redirect
    en producción.
    """
    if not libro_field:
        raise Http404("Este libro no tiene archivo asociado.")

    if not settings.DEBUG:
        # Producción: Nginx sirve el archivo; Django solo autentica
        from django.http import HttpResponse
        response = HttpResponse()
        response['X-Accel-Redirect'] = f'/protected-media/{libro_field.name}'
        response['Content-Type'] = content_type
        return response

    # Desarrollo: Django sirve el archivo directamente
    return FileResponse(
        libro_field.open('rb'),
        content_type=content_type,
    )


@login_required
def servir_pdf_protegido(request, ruta):
    """
    Sirve un PDF de /media/libros/ solo a usuarios autenticados
    que tengan acceso al libro según su rol y categorías asignadas.
    """
    libro = _get_libro_o_404('archivo', f'libros/{ruta}')

    if not usuario_puede_ver_libro(request.user, libro):
        raise PermissionDenied

    return _servir_archivo(libro.archivo, 'application/pdf')


@login_required
def servir_portada_protegida(request, ruta):
    """
    Sirve una imagen de portada de /media/portadas/ solo a usuarios
    autenticados que tengan acceso al libro correspondiente.
    """
    libro = _get_libro_o_404('portada', f'portadas/{ruta}')

    if not usuario_puede_ver_libro(request.user, libro):
        raise PermissionDenied

    content_type, _ = mimetypes.guess_type(ruta)
    content_type = content_type or 'image/jpeg'

    return _servir_archivo(libro.portada, content_type)
