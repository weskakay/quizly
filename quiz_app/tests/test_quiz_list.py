from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quiz_app.tests.helpers import create_quiz


class QuizListTests(APITestCase):
    """Covers GET /api/quizzes/."""

    def setUp(self):
        self.user = User.objects.create_user(username='jane', password='x')
        self.other = User.objects.create_user(username='john', password='x')
        self.url = reverse('quiz-list')

    def test_list_returns_only_own_quizzes(self):
        create_quiz(self.user, title='Mine')
        create_quiz(self.other, title='Not mine')
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([quiz['title'] for quiz in response.data], ['Mine'])

    def test_list_is_a_plain_array_newest_first(self):
        create_quiz(self.user, title='Older')
        create_quiz(self.user, title='Newer')
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertIsInstance(response.data, list)
        self.assertEqual(response.data[0]['title'], 'Newer')

    def test_list_fields_match_the_docs(self):
        create_quiz(self.user)
        self.client.force_authenticate(self.user)
        quiz = self.client.get(self.url).data[0]
        self.assertEqual(list(quiz), [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'video_url', 'questions',
        ])
        self.assertEqual(list(quiz['questions'][0]), [
            'id', 'question_title', 'question_options', 'answer',
        ])

    def test_timestamps_are_utc_iso_strings(self):
        create_quiz(self.user)
        self.client.force_authenticate(self.user)
        quiz = self.client.get(self.url).data[0]
        self.assertTrue(quiz['created_at'].endswith('Z'))
        self.assertTrue(quiz['updated_at'].endswith('Z'))

    def test_list_without_login_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_works_with_login_cookie(self):
        create_quiz(self.user)
        self.client.post(
            reverse('login'), {'username': 'jane', 'password': 'x'},
            format='json',
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
