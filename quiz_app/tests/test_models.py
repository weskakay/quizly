from django.contrib.auth.models import User
from django.test import TestCase

from quiz_app.models import Question, Quiz
from quiz_app.tests.helpers import create_quiz


class QuizModelTests(TestCase):
    """Covers the Quiz and Question models."""

    def setUp(self):
        self.user = User.objects.create_user(username='jane', password='x')

    def test_str_returns_titles(self):
        quiz = create_quiz(self.user, title='Python basics', questions=1)
        self.assertEqual(str(quiz), 'Python basics')
        self.assertEqual(str(quiz.questions.first()), 'Question 1')

    def test_newest_quiz_comes_first(self):
        older = create_quiz(self.user, title='Older')
        newer = create_quiz(self.user, title='Newer')
        self.assertEqual(list(Quiz.objects.all()), [newer, older])

    def test_deleting_quiz_deletes_questions(self):
        create_quiz(self.user).delete()
        self.assertFalse(Question.objects.exists())

    def test_deleting_user_deletes_quizzes(self):
        create_quiz(self.user)
        self.user.delete()
        self.assertFalse(Quiz.objects.exists())
