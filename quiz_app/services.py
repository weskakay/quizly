import logging

from django.db import transaction
from rest_framework import serializers

from quiz_app.api.exceptions import QuizGenerationFailed
from quiz_app.models import Question, Quiz
from quiz_app.utils import QuizGenerationError, VideoError, generate_quiz_data

logger = logging.getLogger(__name__)


def create_quiz_from_url(owner, url):
    """Builds a quiz from a YouTube link and stores it for the owner."""
    quiz_data = generate_quiz_or_fail(url)
    return store_quiz(owner, url, quiz_data)


def generate_quiz_or_fail(url):
    """Runs the pipeline, the video's fault is a 400, ours a 500."""
    try:
        return generate_quiz_data(url)
    except VideoError as error:
        raise serializers.ValidationError({'url': [str(error)]}) from error
    except QuizGenerationError as error:
        logger.error('Quiz generation failed: %s', error, exc_info=True)
        raise QuizGenerationFailed() from error


def store_quiz(owner, url, quiz_data):
    """Saves quiz and questions together or not at all."""
    with transaction.atomic():
        quiz = Quiz.objects.create(
            owner=owner,
            title=quiz_data['title'],
            description=quiz_data['description'],
            video_url=url,
        )
        Question.objects.bulk_create(
            Question(quiz=quiz, **question)
            for question in quiz_data['questions']
        )
    return quiz
