from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class TokenRefreshTests(APITestCase):
    """Covers POST /api/token/refresh/."""

    def setUp(self):
        User.objects.create_user(username='jane', password='secret123')
        self.client.post(
            reverse('login'),
            {'username': 'jane', 'password': 'secret123'},
            format='json',
        )
        self.url = reverse('token-refresh')

    def test_refresh_returns_200_and_new_access_cookie(self):
        old_access = self.client.cookies['access_token'].value
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'detail': 'Token refreshed'})
        cookie = response.cookies['access_token']
        self.assertTrue(cookie['httponly'])
        self.assertNotEqual(cookie.value, old_access)

    def test_refresh_does_not_touch_refresh_cookie(self):
        response = self.client.post(self.url)
        self.assertNotIn('refresh_token', response.cookies)

    def test_missing_refresh_cookie_returns_401(self):
        del self.client.cookies['refresh_token']
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_refresh_cookie_returns_401(self):
        self.client.cookies['refresh_token'] = 'garbage'
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_is_not_accepted_as_refresh(self):
        access = self.client.cookies['access_token'].value
        self.client.cookies['refresh_token'] = access
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
