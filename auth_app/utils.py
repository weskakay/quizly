from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


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


def delete_token_cookies(response):
    """Removes both JWT cookies from the browser."""
    for kind in ('access', 'refresh'):
        response.delete_cookie(f'{kind}_token', samesite='Lax')


def blacklist_refresh_token(raw_token):
    """Puts the refresh token on the blacklist so it cannot be used again.

    A missing, broken or already blacklisted token has nothing left to
    block, the logout goes on anyway.
    """
    if not raw_token:
        return
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        pass
