import logging

from django.db.models import F

from .models import EstadisticaUsuario, VisitaUsuario

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """
    Añade cabeceras HTTP de seguridad que el SecurityMiddleware de Django
    no cubre por defecto:

    - Content-Security-Policy: restringe los orígenes desde los que el
      navegador puede cargar recursos (scripts, estilos, fuentes, imágenes).
      Reduce drásticamente la superficie de ataque XSS.

    - Permissions-Policy: deshabilita APIs del navegador que la aplicación
      no necesita (cámara, micrófono, geolocalización, etc.).

    Orígenes externos requeridos por la aplicación:
      · https://cdn.tailwindcss.com   — Tailwind Play CDN
      · https://cdn.jsdelivr.net      — Alpine.js
      · https://fonts.googleapis.com  — Google Fonts (CSS)
      · https://fonts.gstatic.com     — Google Fonts (archivos de fuente)
      · https://cdnjs.cloudflare.com  — Font Awesome (CSS + webfonts)

    Tailwind CDN y Alpine.js requieren 'unsafe-inline' y 'unsafe-eval' en
    script-src porque generan estilos y evalúan expresiones dinámicamente.
    Si en el futuro se migra a Tailwind compilado localmente, esas directivas
    pueden eliminarse para un CSP más estricto.
    """

    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
        "https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' "
        "https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' "
        "https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "worker-src 'self' blob:; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )

    _PERMISSIONS = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "interest-cohort=()"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = self._CSP
        response["Permissions-Policy"] = self._PERMISSIONS
        return response

# Rutas que no deben registrarse como visitas
_EXCLUDED_PREFIXES = ('/static/', '/media/', '/favicon.ico')


class RegistroVisitasMiddleware:
    """
    Middleware que registra cada visita de usuario autenticado.

    Excluye rutas de archivos estáticos y media para no contaminar
    el registro con peticiones de recursos.

    Cambios respecto a la versión anterior:
        - Se corrige el campo requerido pagina_visitada.
        - Se usa F() para incrementar el contador de forma atómica
          (evita race conditions con múltiples workers simultáneos).
        - Se añade try/except para que un fallo en el tracking
          nunca interrumpa la petición del usuario.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (
            request.user.is_authenticated
            and not request.path.startswith(_EXCLUDED_PREFIXES)
        ):
            try:
                self._registrar_visita(request)
            except Exception:
                logger.exception(
                    "Error al registrar visita para '%s' en '%s'",
                    request.user.email,
                    request.path,
                )

        return response

    def _registrar_visita(self, request):
        usuario = request.user
        ip      = self._get_client_ip(request)

        # get_or_create garantiza que el registro exista;
        # update con F() incrementa el contador de forma atómica.
        EstadisticaUsuario.objects.get_or_create(usuario=usuario)
        EstadisticaUsuario.objects.filter(usuario=usuario).update(
            total_visitas=F('total_visitas') + 1,
        )
        # ultima_visita se actualiza automáticamente por auto_now=True al guardar,
        # pero update() no llama a save(). Lo actualizamos explícitamente.
        from django.utils.timezone import now
        EstadisticaUsuario.objects.filter(usuario=usuario).update(
            ultima_visita=now(),
        )

        VisitaUsuario.objects.create(
            usuario=usuario,
            ip_address=ip,
            pagina_visitada=request.path[:255],
        )

    def _get_client_ip(self, request) -> str:
        """
        Obtiene la IP real del cliente.
        Cloudflare añade CF-Connecting-IP con la IP original, que no puede
        ser falsificada desde el cliente (Cloudflare lo sobrescribe).
        """
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
        if cf_ip:
            return cf_ip
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
