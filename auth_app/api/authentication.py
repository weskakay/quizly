from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from the HttpOnly cookie, not from a header.

    The frontend never sees the token, the browser sends the cookie along
    with every request.
    """

    def authenticate(self, request):
        """Returns (user, token) or None when no access cookie is sent."""
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
