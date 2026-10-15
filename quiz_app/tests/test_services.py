from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import serializers

from quiz_app.api.exceptions import QuizGenerationFailed
from quiz_app.models import Question, Quiz
from quiz_app.services import create_quiz_from_url
from quiz_app.tests.helpers import quiz_answer
from quiz_app.utils import QuizGenerationError, VideoError

PIPELINE = 'quiz_app.services.generate_quiz_data'
URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


class CreateQuizFromUrlTests(TestCase):
    """Covers the service that builds and stores a quiz."""

    def setUp(self):
        self.user = User.objects.create_user(username='jane', password='x')

    @patch(PIPELINE, return_value=quiz_answer())
    def test_quiz_and_questions_are_stored(self, pipeline):
        quiz = create_quiz_from_url(self.user, URL)
        self.assertEqual(quiz.owner, self.user)
        self.assertEqual(quiz.video_url, URL)
        self.assertEqual(quiz.questions.count(), 10)

    @patch(PIPELINE, side_effect=VideoError('Video could not be loaded.'))
    def test_video_error_becomes_validation_error(self, pipeline):
        with self.assertRaises(serializers.ValidationError):
            create_quiz_from_url(self.user, URL)
        self.assertFalse(Quiz.objects.exists())

    @patch(PIPELINE, side_effect=QuizGenerationError('gemini down'))
    def test_generation_error_becomes_quiz_generation_failed(self, pipeline):
        with self.assertLogs('quiz_app.services', level='ERROR'):
            with self.assertRaises(QuizGenerationFailed):
                create_quiz_from_url(self.user, URL)
        self.assertFalse(Question.objects.exists())
