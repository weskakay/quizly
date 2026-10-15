from django import forms
from django.contrib import admin

from quiz_app.models import Question, Quiz
from quiz_app.utils import options_are_valid


class QuestionAdminForm(forms.ModelForm):
    """Keeps edited questions playable: four different options, one answer."""

    class Meta:
        model = Question
        fields = ['question_title', 'question_options', 'answer']

    def clean(self):
        """Rejects option lists the frontend cannot show."""
        data = super().clean()
        options = data.get('question_options')
        if not options_are_valid(options, data.get('answer')):
            raise forms.ValidationError(
                'Four different options are needed, the answer must be one '
                'of them.'
            )
        return data


class QuestionInline(admin.StackedInline):
    """Edit the questions right on the quiz page."""

    model = Question
    form = QuestionAdminForm
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin list of all quizzes with their questions inline."""

    list_display = ['title', 'owner', 'created_at']
    search_fields = ['title', 'description', 'owner__username']
    list_select_related = ['owner']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin list of single questions across all quizzes."""

    form = QuestionAdminForm
    list_display = ['question_title', 'quiz', 'answer']
    search_fields = ['question_title', 'quiz__title']
    list_select_related = ['quiz']
