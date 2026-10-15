from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import (
    CreatedQuizSerializer,
    QuizCreateSerializer,
    QuizSerializer,
)
from quiz_app.models import Quiz
from quiz_app.services import create_quiz_from_url


class QuizListView(generics.ListCreateAPIView):
    """GET /api/quizzes/ lists the own quizzes, POST creates one from a link.

    POST runs synchronously and takes a while: download, transcription and
    the Gemini request happen before the 201.
    """

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only the quizzes of the logged in user, newest first."""
        return super().get_queryset().filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """Checks the link, builds the quiz and answers with it.

        The request only carries a url, the answer is the full new quiz,
        so input and output use different serializers.
        """
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data['video_url']
        quiz = create_quiz_from_url(request.user, url)
        return Response(
            CreatedQuizSerializer(quiz).data, status=status.HTTP_201_CREATED
        )


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PATCH and DELETE /api/quizzes/<id>/ for the owner only.

    A missing quiz gives 404, a quiz of another user 403. PUT is not part
    of the API, title and description change through PATCH.
    """

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
