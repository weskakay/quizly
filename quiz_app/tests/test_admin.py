from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from quiz_app.admin import QuestionAdminForm
from quiz_app.tests.helpers import create_quiz


class QuizAdminTests(TestCase):
    """Covers editing quizzes and single questions in the admin."""

    def setUp(self):
        admin = User.objects.create_superuser('admin', 'a@example.com', 'x')
        self.client.force_login(admin)
        self.quiz = create_quiz(admin)

    def form(self, options, answer):
        return QuestionAdminForm(data={
            'question_title': 'Q',
            'question_options': options,
            'answer': answer,
        })

    def test_quiz_page_shows_questions_inline(self):
        url = reverse('admin:quiz_app_quiz_change', args=[self.quiz.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'Question 1')

    def test_question_list_page_loads(self):
        url = reverse('admin:quiz_app_question_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_form_accepts_four_options_with_answer(self):
        self.assertTrue(self.form('["A", "B", "C", "D"]', 'A').is_valid())

    def test_form_rejects_wrong_option_count(self):
        self.assertFalse(self.form('["A", "B"]', 'A').is_valid())

    def test_form_rejects_duplicate_options(self):
        for options in ('["A", "A", "B", "C"]', '["A", "A", "B", "C", "D"]'):
            with self.subTest(options=options):
                self.assertFalse(self.form(options, 'A').is_valid())

    def test_form_rejects_nested_options_without_crash(self):
        self.assertFalse(self.form('[[1], [1], [2], [3]]', '[1]').is_valid())

    def test_form_rejects_answer_outside_options(self):
        self.assertFalse(self.form('["A", "B", "C", "D"]', 'E').is_valid())
