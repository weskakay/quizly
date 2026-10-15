from rest_framework import generics
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from auth_app.api.serializers import RegistrationSerializer
from auth_app.utils import (
    blacklist_refresh_token,
    delete_token_cookies,
    set_access_cookie,
    set_refresh_cookie,
)


class RegistrationView(generics.CreateAPIView):
    """POST /api/register/ creates a new account.

    No authentication runs here, so an expired cookie sent by the
    frontend cannot block the request.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer


class LoginView(TokenObtainPairView):
    """POST /api/login/ checks the credentials and sets both JWT cookies.

    Wrong credentials end in a 401 with a general message from simplejwt.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Logs the user in and stores the tokens in HttpOnly cookies."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        response = Response({
            'detail': 'Login successfully!',
            'user': {'id': user.id, 'username': user.username,
                     'email': user.email},
        })
        set_access_cookie(response, serializer.validated_data['access'])
        set_refresh_cookie(response, serializer.validated_data['refresh'])
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """POST /api/token/refresh/ issues a new access cookie.

    The refresh token comes from its cookie, the request body stays empty.
    Errors end in a 401, the parent view sends the WWW-Authenticate header.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Checks the refresh cookie and sets a fresh access cookie."""
        raw_token = request.COOKIES.get('refresh_token')
        if not raw_token:
            raise NotAuthenticated('Refresh token is missing.')
        serializer = self.get_serializer(data={'refresh': raw_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as error:
            raise InvalidToken(error.args[0]) from error
        response = Response({'detail': 'Token refreshed'})
        set_access_cookie(response, serializer.validated_data['access'])
        return response


class LogoutView(APIView):
    """POST /api/logout/ blacklists the refresh token and clears cookies."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Logs the user out, old tokens cannot be refreshed afterwards."""
        blacklist_refresh_token(request.COOKIES.get('refresh_token'))
        response = Response({
            'detail': 'Log-Out successfully! All Tokens will be deleted. '
                      'Refresh token is now invalid.'
        })
        delete_token_cookies(response)
        return response
