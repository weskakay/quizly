from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def set_token_cookie(response, name, token, lifetime):
    """Stores a JWT in an HttpOnly cookie that expires with the token."""
    response.set_cookie(
        name,
        str(token),
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite='Lax',
    )


def set_access_cookie(response, token):
    """Sets the short lived access token cookie."""
    lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    set_token_cookie(response, 'access_token', token, lifetime)


def set_refresh_cookie(response, token):
    """Sets the refresh token cookie."""
    lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
    set_token_cookie(response, 'refresh_token', token, lifetime)


def delete_token_cookies(response):
    """Removes both JWT cookies from the browser."""
    response.delete_cookie('access_token', samesite='Lax')
    response.delete_cookie('refresh_token', samesite='Lax')


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
