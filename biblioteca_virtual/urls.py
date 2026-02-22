"""
URL configuration for biblioteca_virtual project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from library.views.media import servir_pdf_protegido, servir_portada_protegida

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Archivos media protegidos por autenticación ─────────────────────────
    # Estas rutas deben ir ANTES de include('library.urls') para interceptar
    # cualquier solicitud a /media/libros/ y /media/portadas/.
    path('media/libros/<path:ruta>',   servir_pdf_protegido,    name='servir_pdf'),
    path('media/portadas/<path:ruta>', servir_portada_protegida, name='servir_portada'),

    # ── Rutas de la aplicación ──────────────────────────────────────────────
    path('', include('library.urls')),
]

if settings.DEBUG:
    # Solo archivos estáticos en desarrollo — los media van por las rutas
    # protegidas definidas arriba, no por el servidor estático de Django.
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)