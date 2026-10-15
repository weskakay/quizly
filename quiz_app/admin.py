from django import forms
from django.contrib import admin

from quiz_app.models import Question, Quiz


class QuestionAdminForm(forms.ModelForm):
    """Keeps edited questions playable: four different options, one answer."""

    class Meta:
        model = Question
        fields = ['question_title', 'question_options', 'answer']

    def clean(self):
        """Rejects option lists the frontend cannot show."""
        data = super().clean()
        options = data.get('question_options')
        if not isinstance(options, list) or len(options) != 4:
            raise forms.ValidationError('Exactly four options are needed.')
        if len({str(option) for option in options}) != 4:
            raise forms.ValidationError('The four options must differ.')
        if data.get('answer') not in options:
            raise forms.ValidationError('The answer must be one option.')
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
