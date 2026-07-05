from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += (
    'rest_framework.authentication.SessionAuthentication',
)
