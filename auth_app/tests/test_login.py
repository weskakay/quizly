from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class LoginTests(APITestCase):
    """Covers POST /api/login/."""

    def setUp(self):
        self.url = reverse('login')
        self.user = User.objects.create_user(
            username='jane', email='jane@example.com', password='secret123'
        )
        self.payload = {'username': 'jane', 'password': 'secret123'}

    def post(self, payload=None):
        data = self.payload if payload is None else payload
        return self.client.post(self.url, data, format='json')

    def test_login_returns_200_with_user(self):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'detail': 'Login successfully!',
            'user': {'id': self.user.id, 'username': 'jane',
                     'email': 'jane@example.com'},
        })

    def test_login_sets_httponly_cookies(self):
        response = self.post()
        for name in ('access_token', 'refresh_token'):
            cookie = response.cookies[name]
            self.assertTrue(cookie.value)
            self.assertTrue(cookie['httponly'])
            self.assertEqual(cookie['samesite'], 'Lax')

    def test_cookies_live_as_long_as_tokens(self):
        response = self.post()
        self.assertEqual(response.cookies['access_token']['max-age'], 300)
        self.assertEqual(response.cookies['refresh_token']['max-age'], 86400)

    def test_tokens_are_not_in_body(self):
        response = self.post()
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_wrong_password_returns_401(self):
        self.payload['password'] = 'wrong'
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
        self.assertNotIn('access_token', response.cookies)
        self.assertNotIn('refresh_token', response.cookies)

    def test_inactive_user_returns_401(self):
        self.user.is_active = False
        self.user.save()
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_user_gets_same_message(self):
        wrong_password = self.post({'username': 'jane', 'password': 'x'})
        unknown_user = self.post({'username': 'nobody', 'password': 'x'})
        self.assertEqual(unknown_user.status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(unknown_user.data, wrong_password.data)

    def test_missing_fields_return_400(self):
        response = self.post({})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_cookie_does_not_block_login(self):
        self.client.cookies['access_token'] = 'expired'
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
