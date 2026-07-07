from django.conf import settings


def _cookie_kwargs(max_age=None):
    kwargs = {
        'max_age': max_age,
        'httponly': settings.JWT_COOKIE_HTTPONLY,
        'secure': settings.JWT_COOKIE_SECURE,
        'samesite': settings.JWT_COOKIE_SAMESITE,
        'path': settings.JWT_COOKIE_PATH,
    }
    if settings.JWT_COOKIE_DOMAIN:
        kwargs['domain'] = settings.JWT_COOKIE_DOMAIN
    return kwargs


def set_auth_cookies(response, *, access=None, refresh=None):
    if access is not None:
        response.set_cookie(
            settings.JWT_ACCESS_COOKIE_NAME,
            access,
            **_cookie_kwargs(max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())),
        )
    if refresh is not None:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE_NAME,
            refresh,
            **_cookie_kwargs(max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())),
        )
    return response


def clear_auth_cookies(response):
    delete_kwargs = {
        'path': settings.JWT_COOKIE_PATH,
        'samesite': settings.JWT_COOKIE_SAMESITE,
    }
    if settings.JWT_COOKIE_DOMAIN:
        delete_kwargs['domain'] = settings.JWT_COOKIE_DOMAIN
    response.delete_cookie(settings.JWT_ACCESS_COOKIE_NAME, **delete_kwargs)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME, **delete_kwargs)
    return response
