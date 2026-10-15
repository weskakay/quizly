from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from quiz_app.api.permissions import IsQuizOwner
from quiz_app.api.serializers import QuizCreateSerializer, QuizSerializer
from quiz_app.models import Quiz


class QuizListView(generics.ListCreateAPIView):
    """GET /api/quizzes/ lists the own quizzes, POST creates one from a link.

    POST runs synchronously and takes a while: download, transcription and
    the Gemini request happen before the 201.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only the own quizzes, newest first, questions in one query."""
        return Quiz.objects.filter(
            owner=self.request.user
        ).prefetch_related('questions')

    def get_serializer_class(self):
        """The create serializer takes a url, the list shows quizzes."""
        if self.request.method == 'POST':
            return QuizCreateSerializer
        return QuizSerializer

    def perform_create(self, serializer):
        """Stores the quiz for the logged in user."""
        serializer.save(owner=self.request.user)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PATCH and DELETE /api/quizzes/<id>/ for the owner only.

    A missing quiz gives 404, a quiz of another user 403. PUT is not part
    of the API, title and description change through PATCH.
    """

    queryset = Quiz.objects.prefetch_related('questions')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsQuizOwner]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
