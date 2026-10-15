from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quiz_app.models import Question, Quiz
from quiz_app.tests.helpers import quiz_answer
from quiz_app.utils import QuizGenerationError, VideoError

PIPELINE = 'quiz_app.services.generate_quiz_data'


class QuizCreateTests(APITestCase):
    """Covers POST /api/quizzes/ with the pipeline faked."""

    def setUp(self):
        self.user = User.objects.create_user(username='jane', password='x')
        self.client.force_authenticate(self.user)
        self.url = reverse('quiz-list')
        self.payload = {'url': 'https://youtu.be/dQw4w9WgXcQ?si=abc'}

    def post(self, payload=None):
        data = self.payload if payload is None else payload
        return self.client.post(self.url, data, format='json')

    @patch(PIPELINE, return_value=quiz_answer())
    def test_create_returns_201_with_full_quiz(self, pipeline):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['video_url'],
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )
        self.assertEqual(len(response.data['questions']), 10)
        pipeline.assert_called_once_with(response.data['video_url'])

    @patch(PIPELINE, return_value=quiz_answer())
    def test_create_fields_match_the_docs(self, pipeline):
        quiz = self.post().data
        self.assertEqual(list(quiz), [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'video_url', 'questions',
        ])
        self.assertEqual(list(quiz['questions'][0]), [
            'id', 'question_title', 'question_options', 'answer',
            'created_at', 'updated_at',
        ])

    @patch(PIPELINE, return_value=quiz_answer())
    def test_quiz_is_stored_for_the_user(self, pipeline):
        self.post()
        quiz = Quiz.objects.get()
        self.assertEqual(quiz.owner, self.user)
        self.assertEqual(quiz.questions.count(), 10)

    @patch(PIPELINE)
    def test_invalid_url_returns_400_before_pipeline(self, pipeline):
        for payload in ({'url': 'https://vimeo.com/1'}, {'url': ''}, {}):
            with self.subTest(payload=payload):
                response = self.post(payload)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn('url', response.data)
        pipeline.assert_not_called()

    @patch(PIPELINE, side_effect=VideoError('Video could not be loaded.'))
    def test_unusable_video_returns_400(self, pipeline):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {'url': ['Video could not be loaded.']}
        )
        self.assertFalse(Quiz.objects.exists())

    @patch(PIPELINE, side_effect=QuizGenerationError('gemini down'))
    def test_failed_generation_returns_500_without_details(self, pipeline):
        with self.assertLogs('quiz_app.services', level='ERROR'):
            response = self.post()
        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertEqual(
            response.data, {'detail': 'Quiz could not be generated.'}
        )
        self.assertFalse(Question.objects.exists())

    def test_create_without_login_returns_401(self):
        self.client.force_authenticate(None)
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(PIPELINE, return_value=quiz_answer())
    def test_created_quiz_appears_in_list(self, pipeline):
        self.post()
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn('created_at', response.data[0]['questions'][0])
