import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from quiz_app.tests.helpers import quiz_answer
from quiz_app.utils import (
    QuizGenerationError,
    ask_gemini_for_quiz,
    build_prompt,
    parse_quiz,
    strip_code_fences,
)

BROKEN_QUESTIONS = [
    {'question_options': ['A', 'B', 'C']},
    {'question_options': ['A', 'A', 'B', 'C']},
    {'question_options': ['A', 'B', 'C', '']},
    {'question_options': 'A, B, C, D'},
    {'answer': 'E'},
    {'question_title': ''},
]


class ParseQuizTests(SimpleTestCase):
    """Covers cleaning and checking the Gemini answer."""

    def test_code_fences_are_removed(self):
        for text in ('```json\n{"a": 1}\n```', '```\n{"a": 1}\n```',
                     '{"a": 1}'):
            with self.subTest(text=text):
                self.assertEqual(strip_code_fences(text), '{"a": 1}')

    def test_valid_answer_is_parsed_and_trimmed(self):
        data = quiz_answer()
        data['questions'][0]['answer'] = ' B '
        data['questions'][0]['question_options'][1] = 'B  '
        quiz = parse_quiz('```json\n' + json.dumps(data) + '\n```')
        self.assertEqual(len(quiz['questions']), 10)
        self.assertEqual(quiz['questions'][0]['answer'], 'B')

    def test_broken_answers_are_rejected(self):
        broken = [
            'no json at all',
            json.dumps(['a list']),
            json.dumps({'title': 'x', 'questions': 'none'}),
            json.dumps(quiz_answer(questions=9)),
            json.dumps(dict(quiz_answer(), title='')),
        ]
        for text in broken:
            with self.subTest(text=text[:30]):
                with self.assertRaises(QuizGenerationError):
                    parse_quiz(text)

    def test_broken_questions_are_rejected(self):
        for change in BROKEN_QUESTIONS:
            with self.subTest(change=change):
                data = quiz_answer()
                data['questions'][3].update(change)
                with self.assertRaises(QuizGenerationError):
                    parse_quiz(json.dumps(data))

    def test_question_that_is_no_object_is_rejected(self):
        data = quiz_answer()
        data['questions'][0] = 'just text'
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps(data))

    def test_prompt_contains_transcript_and_language_rule(self):
        prompt = build_prompt('Hallo zusammen')
        self.assertTrue(prompt.endswith('Hallo zusammen'))
        self.assertIn('language of the', prompt)


@override_settings(GEMINI_MODELS=['first', 'second'])
class AskGeminiTests(SimpleTestCase):
    """Covers falling back to the next model."""

    @patch('quiz_app.utils.request_quiz_text')
    def test_first_model_answers(self, request):
        request.return_value = json.dumps(quiz_answer())
        quiz = ask_gemini_for_quiz('prompt')
        self.assertEqual(quiz['title'], 'Elephants')
        request.assert_called_once_with('prompt', 'first')

    @patch('quiz_app.utils.request_quiz_text')
    def test_next_model_steps_in(self, request):
        request.side_effect = [
            QuizGenerationError('overloaded'), json.dumps(quiz_answer()),
        ]
        with self.assertLogs('quiz_app.utils', level='WARNING'):
            quiz = ask_gemini_for_quiz('prompt')
        self.assertEqual(quiz['title'], 'Elephants')
        self.assertEqual(request.call_args.args, ('prompt', 'second'))

    @patch('quiz_app.utils.request_quiz_text')
    def test_error_when_all_models_fail(self, request):
        request.return_value = 'not json'
        with self.assertLogs('quiz_app.utils', level='WARNING'):
            with self.assertRaises(QuizGenerationError):
                ask_gemini_for_quiz('prompt')
        self.assertEqual(request.call_count, 2)

    @override_settings(GEMINI_MODELS=[])
    def test_error_without_models(self):
        with self.assertRaises(QuizGenerationError):
            ask_gemini_for_quiz('prompt')
