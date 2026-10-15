from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

STRONG_PASSWORD = 'Quizly-Test-2026'


class RegistrationTests(APITestCase):
    """Covers POST /api/register/."""

    def setUp(self):
        self.url = reverse('register')
        self.payload = {
            'username': 'jane',
            'email': 'jane@example.com',
            'password': STRONG_PASSWORD,
            'confirmed_password': STRONG_PASSWORD,
        }

    def post(self):
        return self.client.post(self.url, self.payload, format='json')

    def test_registration_returns_201_with_detail(self):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data, {'detail': 'User created successfully!'}
        )

    def test_password_is_stored_hashed(self):
        self.post()
        user = User.objects.get(username='jane')
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_mismatched_passwords_return_400(self):
        self.payload['confirmed_password'] = 'other'
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_password', response.data)
        self.assertFalse(User.objects.filter(username='jane').exists())

    def test_weak_passwords_return_400(self):
        for password in ('123', 'password', '12345678', 'secret123'):
            with self.subTest(password=password):
                self.payload['password'] = password
                self.payload['confirmed_password'] = password
                response = self.post()
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn('password', response.data)
        self.assertFalse(User.objects.filter(username='jane').exists())

    def test_duplicate_username_returns_400(self):
        User.objects.create_user(username='jane', email='x@example.com')
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_duplicate_email_ignores_case(self):
        User.objects.create_user(username='john', email='Jane@Example.com')
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_invalid_email_returns_400(self):
        self.payload['email'] = 'not-an-email'
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_blank_email_returns_400(self):
        self.payload['email'] = ''
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertFalse(User.objects.filter(username='jane').exists())

    def test_missing_fields_return_400(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in self.payload:
            self.assertIn(field, response.data)

    def test_expired_cookie_does_not_block_registration(self):
        self.client.cookies['access_token'] = 'expired'
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
