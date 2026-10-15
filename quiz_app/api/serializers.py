import logging

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from quiz_app.models import Question, Quiz
from quiz_app.utils import (
    QuizGenerationError,
    VideoError,
    generate_quiz_data,
    normalize_youtube_url,
)

logger = logging.getLogger(__name__)


class QuizGenerationFailed(APIException):
    """500 with a general message, details only go to the log."""

    status_code = 500
    default_detail = 'Quiz could not be generated.'
    default_code = 'quiz_generation_failed'


class QuestionSerializer(serializers.ModelSerializer):
    """One question as the quiz list, detail and update return it."""

    class Meta:
        model = Question
        fields = ['id', 'question_title', 'question_options', 'answer']


class QuizSerializer(serializers.ModelSerializer):
    """A quiz with its questions, only title and description are editable."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'created_at', 'updated_at',
            'video_url', 'questions',
        ]
        read_only_fields = ['created_at', 'updated_at', 'video_url']


class CreatedQuestionSerializer(QuestionSerializer):
    """A new question, the create response also shows its timestamps."""

    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ['created_at', 'updated_at']


class CreatedQuizSerializer(QuizSerializer):
    """The quiz as POST /api/quizzes/ returns it."""

    questions = CreatedQuestionSerializer(many=True, read_only=True)


class QuizCreateSerializer(serializers.Serializer):
    """Takes a YouTube link and builds a quiz with 10 questions from it."""

    url = serializers.CharField()

    def validate_url(self, value):
        """Rejects anything that is not a YouTube video before downloading."""
        try:
            return normalize_youtube_url(value)
        except VideoError as error:
            raise serializers.ValidationError(str(error)) from error

    def create(self, validated_data):
        """Runs the pipeline and stores the quiz with its questions."""
        url = validated_data['url']
        quiz_data = self._generate(url)
        return self._store(validated_data['owner'], url, quiz_data)

    def _generate(self, url):
        """Maps pipeline errors: the video's fault 400, ours 500."""
        try:
            return generate_quiz_data(url)
        except VideoError as error:
            raise serializers.ValidationError({'url': [str(error)]}) from error
        except QuizGenerationError as error:
            logger.error('Quiz generation failed: %s', error, exc_info=True)
            raise QuizGenerationFailed() from error

    def _store(self, owner, url, quiz_data):
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

    def to_representation(self, instance):
        """Answers with the full quiz instead of the posted url."""
        return CreatedQuizSerializer(instance).data
