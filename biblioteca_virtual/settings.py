"""
Django settings for biblioteca_virtual project.
Los valores sensibles se leen desde el archivo .env (nunca subir .env a git).
Copia .env.example a .env y completa los valores antes de ejecutar.
"""

from pathlib import Path
import os
import environ

# ─────────────────────────────────────────────────────────────────────────────
# Rutas base
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Inicializar environ y leer el archivo .env
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    DATA_UPLOAD_MAX_MEMORY_SIZE=(int, 524_288_000),
    FILE_UPLOAD_MAX_MEMORY_SIZE=(int, 524_288_000),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / '.env')


# ─────────────────────────────────────────────────────────────────────────────
# Seguridad central
# ─────────────────────────────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])


# ─────────────────────────────────────────────────────────────────────────────
# Aplicaciones instaladas
# ─────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'library',
    'rest_framework',
    'corsheaders',
]


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'library.middleware.SecurityHeadersMiddleware',   # CSP + Permissions-Policy
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'library.middleware.RegistroVisitasMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# ─────────────────────────────────────────────────────────────────────────────
# Autenticación
# ─────────────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'library.CustomUser'
LOGIN_URL = 'library:login'
LOGIN_REDIRECT_URL = 'library:dashboard'
LOGOUT_REDIRECT_URL = 'library:login'

# Sesiones — expiran en 8 horas o al cerrar el navegador
SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# ─────────────────────────────────────────────────────────────────────────────
# URLs y WSGI
# ─────────────────────────────────────────────────────────────────────────────
ROOT_URLCONF = 'biblioteca_virtual.urls'
WSGI_APPLICATION = 'biblioteca_virtual.wsgi.application'


# ─────────────────────────────────────────────────────────────────────────────
# Templates
# ─────────────────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'library/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Base de datos
# Desarrollo: SQLite. Producción: configurar DATABASE_URL en .env
# Ejemplo producción: DATABASE_URL=postgresql://user:pass@localhost/biblioteca
# ─────────────────────────────────────────────────────────────────────────────
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'
    )
}


# ─────────────────────────────────────────────────────────────────────────────
# Validación de contraseñas
# ─────────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─────────────────────────────────────────────────────────────────────────────
# Internacionalización
# ─────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# ─────────────────────────────────────────────────────────────────────────────
# Archivos estáticos y media
# ─────────────────────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'library/static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Permite subir ZIPs de hasta 500 MB (carga masiva de libros)
DATA_UPLOAD_MAX_MEMORY_SIZE = env('DATA_UPLOAD_MAX_MEMORY_SIZE')
FILE_UPLOAD_MAX_MEMORY_SIZE = env('FILE_UPLOAD_MAX_MEMORY_SIZE')


# ─────────────────────────────────────────────────────────────────────────────
# CORS y CSRF
# ─────────────────────────────────────────────────────────────────────────────
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:3000'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost:3000'])


# ─────────────────────────────────────────────────────────────────────────────
# Django REST Framework
# ─────────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# API.Bible — Versículo del Día
# Obtén tu API key en: https://scripture.api.bible/
# ─────────────────────────────────────────────────────────────────────────────
BIBLE_API_KEY = env('BIBLE_API_KEY', default='')   # Ya no se usa (API gratuita)
BIBLE_ID      = env('BIBLE_ID', default='')          # Ya no se usa (API gratuita)


# ─────────────────────────────────────────────────────────────────────────────
# Email — Notificaciones automáticas vía Brevo SMTP
# Configura las credenciales en .env (ver .env.example)
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_BACKEND   = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST      = env('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT      = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS   = True
EMAIL_HOST_USER     = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = env('DEFAULT_FROM_EMAIL', default='Biblioteca Virtual <notificaciones@ministeriopozodejacob.cl>')
EMAIL_TIMEOUT   = 10   # seg — evita que un SMTP lento bloquee el request

# URL pública del sitio (usada en los links de los emails)
SITE_URL = env('SITE_URL', default='http://localhost:8000')


# ─────────────────────────────────────────────────────────────────────────────
# Seguridad en producción (se activa automáticamente cuando DEBUG=False)
# ─────────────────────────────────────────────────────────────────────────────
if not DEBUG:
    # Indica a Django que confíe en el header que envía Nginx (proxy inverso)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Nginx ya redirige HTTP→HTTPS, Django no necesita hacerlo de nuevo
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000          # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
