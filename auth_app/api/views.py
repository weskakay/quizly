from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from auth_app.api.serializers import RegistrationSerializer
from auth_app.utils import set_token_cookie


class RegistrationView(generics.CreateAPIView):
    """POST /api/register/ creates a new account.

    No authentication runs here, so an expired cookie sent by the
    frontend cannot block the request.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def create(self, request, *args, **kwargs):
        """Saves the user and answers with a short confirmation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'detail': 'User created successfully!'},
            status=status.HTTP_201_CREATED,
        )


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
        for kind in ('access', 'refresh'):
            set_token_cookie(response, kind, serializer.validated_data[kind])
        return response
