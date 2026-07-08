from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


def enforce_csrf(request):
    check = _CSRFCheck(lambda req: None)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f'CSRF Failed: {reason}')


class CookieJWTAuthentication(JWTAuthentication):
    """JWT auth using HttpOnly access cookie, with Bearer fallback for tooling."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
        if raw_token is None:
            return None

        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            enforce_csrf(request)

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token


class PairingTokenAuthentication(BaseAuthentication):
    keyword = 'X-Kid-Token'

    def authenticate_header(self, request):
        return self.keyword

    def authenticate(self, request):
        token = request.headers.get(self.keyword)
        if not token:
            return None

        try:
            access = AccessToken(token)
            if access.get('scope') != 'kid_device':
                return None

            from apps.children.models import Nino

            nino_id = access.get('nino_id')
            if not nino_id:
                return None

            nino = Nino.objects.get(pk=nino_id)
            return (nino, token)
        except Exception:
            return None
