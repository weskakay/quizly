from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quiz_app.models import Question, Quiz
from quiz_app.tests.helpers import create_quiz


class QuizDetailTests(APITestCase):
    """Covers GET, PATCH and DELETE /api/quizzes/<id>/."""

    def setUp(self):
        self.user = User.objects.create_user(username='jane', password='x')
        self.other = User.objects.create_user(username='john', password='x')
        self.quiz = create_quiz(self.user)
        self.url = reverse('quiz-detail', args=[self.quiz.id])
        self.client.force_authenticate(self.user)

    def test_get_returns_200_with_questions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.quiz.id)
        self.assertEqual(len(response.data['questions']), 2)

    def test_patch_changes_title_and_description(self):
        response = self.client.patch(
            self.url, {'title': 'New', 'description': 'Changed'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'New')
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.description, 'Changed')

    def test_patch_ignores_video_url(self):
        self.client.patch(
            self.url, {'video_url': 'https://example.com'}, format='json'
        )
        self.quiz.refresh_from_db()
        self.assertIn('youtube.com', self.quiz.video_url)

    def test_patch_with_empty_title_returns_400(self):
        response = self.client.patch(self.url, {'title': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_returns_204_and_removes_questions(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.exists())
        self.assertFalse(Question.objects.exists())

    def test_put_is_not_allowed(self):
        response = self.client.put(self.url, {'title': 'x'}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_missing_quiz_returns_404(self):
        url = reverse('quiz-detail', args=[self.quiz.id + 100])
        for method in ('get', 'patch', 'delete'):
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_quiz_of_other_user_returns_403(self):
        self.client.force_authenticate(self.other)
        for method in ('get', 'patch', 'delete'):
            response = getattr(self.client, method)(self.url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Quiz.objects.filter(id=self.quiz.id).exists())

    def test_without_login_returns_401(self):
        self.client.force_authenticate(None)
        for method in ('get', 'patch', 'delete'):
            response = getattr(self.client, method)(self.url)
            self.assertEqual(
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )
