from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.accounts.authentication.CookieJWTAuthentication'
    name = 'CookieJWTAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': settings.JWT_ACCESS_COOKIE_NAME,
            'description': (
                'JWT access token stored in an HttpOnly cookie. '
                'Authorization: Bearer is also accepted as a development/tooling fallback.'
            ),
        }
