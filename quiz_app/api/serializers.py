from rest_framework import serializers

from quiz_app.models import Question, Quiz
from quiz_app.utils import VideoError, normalize_youtube_url


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


class QuizCreateSerializer(serializers.ModelSerializer):
    """Checks the YouTube link a new quiz is built from."""

    url = serializers.CharField(source='video_url')

    class Meta:
        model = Quiz
        fields = ['url']

    def validate_url(self, value):
        """Rejects anything that is not a YouTube video before downloading."""
        try:
            return normalize_youtube_url(value)
        except VideoError as error:
            raise serializers.ValidationError(str(error)) from error
