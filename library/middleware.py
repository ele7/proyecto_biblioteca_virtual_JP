from django.utils.timezone import now
from .models import EstadisticaUsuario, VisitaUsuario


class RegistroVisitasMiddleware:
    """
    Middleware que registra cada visita de usuario autenticado
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            self.registrar_visita(request)

        return response

    def registrar_visita(self, request):
        usuario = request.user
        ip = self.get_client_ip(request)

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
            ip_address=ip,
        )

    def get_client_ip(self, request):
        """Obtiene la IP del cliente, considerando proxy o load balancer"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")
