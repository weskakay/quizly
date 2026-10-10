from django.apps import AppConfig


class QuizAppConfig(AppConfig):
    """App holding quizzes, their questions and the quiz generation."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quiz_app'
