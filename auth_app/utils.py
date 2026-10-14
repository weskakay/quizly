from django.conf import settings


def set_token_cookie(response, kind, token):
    """Stores a JWT in an HttpOnly cookie that lives as long as the token.

    kind is 'access' or 'refresh', the cookie is named after it.
    """
    lifetime = settings.SIMPLE_JWT[f'{kind.upper()}_TOKEN_LIFETIME']
    response.set_cookie(
        f'{kind}_token',
        str(token),
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite='Lax',
    )
