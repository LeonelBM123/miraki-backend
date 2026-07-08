import json
import logging
from datetime import timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / '.env')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class EnsuringRotatingFileHandler(RotatingFileHandler):
    def __init__(self, filename, *args, **kwargs):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, *args, **kwargs)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Solo necesario para correr Django nativo en Windows (fuera de Docker), donde
# GEOS/GDAL no se auto-detectan como en Linux. En Docker no se definen estas
# variables y Django usa la detección automática normal.
GDAL_LIBRARY_PATH = env('GDAL_LIBRARY_PATH', default=None)
GEOS_LIBRARY_PATH = env('GEOS_LIBRARY_PATH', default=None)

CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    'rest_framework',
    'rest_framework_gis',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_extensions',

    'apps.common',
    'apps.accounts',
    'apps.institutions',
    'apps.children',
    'apps.audit',
    'apps.zones',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL'),
}

AUTH_USER_MODEL = 'accounts.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-bo'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.accounts.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': env('THROTTLE_ANON_RATE', default='5/min'),
        'user': env('THROTTLE_USER_RATE', default='100/hour'),
        'auth': env('THROTTLE_AUTH_RATE', default='10/min'),
    },
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'config.settings.base.JsonFormatter',
        },
    },
    'handlers': {
        'auth_file': {
            'class': 'config.settings.base.EnsuringRotatingFileHandler',
            'filename': env('AUTH_LOG_FILE', default=str(BASE_DIR / 'logs' / 'auth.log')),
            'maxBytes': env.int('AUTH_LOG_MAX_BYTES', default=1_048_576),
            'backupCount': env.int('AUTH_LOG_BACKUP_COUNT', default=5),
            'formatter': 'json',
            'level': env('AUTH_LOG_LEVEL', default='INFO'),
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'auth': {
            'handlers': ['auth_file'],
            'level': env('AUTH_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['auth_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id_usuario',
    'USER_ID_CLAIM': 'user_id',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Miraki API',
    'DESCRIPTION': 'API del sistema de monitoreo infantil Miraki.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = True
# Si no se define CSRF_TRUSTED_ORIGINS, hereda automáticamente los orígenes de CORS
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=CORS_ALLOWED_ORIGINS)

JWT_ACCESS_COOKIE_NAME = env('JWT_ACCESS_COOKIE_NAME', default='miraki_access')
JWT_REFRESH_COOKIE_NAME = env('JWT_REFRESH_COOKIE_NAME', default='miraki_refresh')
JWT_COOKIE_SECURE = env.bool('JWT_COOKIE_SECURE', default=False)
JWT_COOKIE_SAMESITE = env('JWT_COOKIE_SAMESITE', default='Lax')
JWT_COOKIE_DOMAIN = env('JWT_COOKIE_DOMAIN', default=None)
JWT_COOKIE_PATH = env('JWT_COOKIE_PATH', default='/')
JWT_COOKIE_HTTPONLY = True

CELERY_BROKER_URL = env('REDIS_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
