from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


class LogoutTests(APITestCase):
    """Covers POST /api/logout/."""

    def setUp(self):
        User.objects.create_user(username='jane', password='secret123')
        self.client.post(
            reverse('login'),
            {'username': 'jane', 'password': 'secret123'},
            format='json',
        )
        self.url = reverse('logout')

    def test_logout_returns_200_with_detail(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'detail': 'Log-Out successfully! All Tokens will be deleted. '
                      'Refresh token is now invalid.'
        })

    def test_logout_deletes_both_cookies(self):
        response = self.client.post(self.url)
        for name in ('access_token', 'refresh_token'):
            self.assertEqual(response.cookies[name].value, '')
            self.assertEqual(response.cookies[name]['max-age'], 0)

    def test_old_refresh_token_is_blacklisted(self):
        refresh = self.client.cookies['refresh_token'].value
        self.client.post(self.url)
        self.client.cookies['refresh_token'] = refresh
        response = self.client.post(reverse('token-refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_access_cookie_returns_401(self):
        self.client.cookies.clear()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_broken_refresh_cookie_still_works(self):
        self.client.cookies['refresh_token'] = 'garbage'
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_refresh_cookie_stores_no_token(self):
        del self.client.cookies['refresh_token']
        outstanding = OutstandingToken.objects.count()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OutstandingToken.objects.count(), outstanding)
        self.assertFalse(BlacklistedToken.objects.exists())
