from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from auth_app.api.serializers import RegistrationSerializer


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
