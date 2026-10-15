from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    """A quiz generated from one YouTube video, owned by one user.

    CASCADE on owner: a quiz has no meaning without its user, so deleting
    the account removes the quizzes as well.
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quizzes',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'quiz'
        verbose_name_plural = 'quizzes'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title


class Question(models.Model):
    """One question of a quiz with four answer options.

    CASCADE on quiz: questions only exist inside their quiz and go away
    when the quiz is deleted.
    """

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    question_title = models.TextField()
    question_options = models.JSONField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'question'
        verbose_name_plural = 'questions'
        ordering = ['id']

    def __str__(self):
        return self.question_title
