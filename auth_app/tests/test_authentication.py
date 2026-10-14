from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken

from auth_app.api.authentication import CookieJWTAuthentication


class CookieJWTAuthenticationTests(APITestCase):
    """Covers reading the access token from the cookie."""

    def setUp(self):
        self.user = User.objects.create_user(username='jane', password='x')
        self.auth = CookieJWTAuthentication()
        self.factory = APIRequestFactory()

    def request_with_cookie(self, value):
        request = self.factory.get('/')
        request.COOKIES['access_token'] = value
        return request

    def test_valid_cookie_returns_user(self):
        token = str(AccessToken.for_user(self.user))
        user, _ = self.auth.authenticate(self.request_with_cookie(token))
        self.assertEqual(user, self.user)

    def test_missing_cookie_returns_none(self):
        self.assertIsNone(self.auth.authenticate(self.factory.get('/')))

    def test_invalid_cookie_raises(self):
        with self.assertRaises(InvalidToken):
            self.auth.authenticate(self.request_with_cookie('garbage'))

    def test_bearer_header_is_ignored(self):
        token = str(AccessToken.for_user(self.user))
        request = self.factory.get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertIsNone(self.auth.authenticate(request))
