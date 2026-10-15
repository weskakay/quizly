from rest_framework import status
from rest_framework.exceptions import APIException


class QuizGenerationFailed(APIException):
    """500 with a general message, details only go to the log."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Quiz could not be generated.'
    default_code = 'quiz_generation_failed'
