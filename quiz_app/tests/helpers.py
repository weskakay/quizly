from quiz_app.models import Question, Quiz


def create_quiz(owner, title='Quiz', questions=2):
    """Creates a quiz with a few playable questions for the tests."""
    quiz = Quiz.objects.create(
        owner=owner,
        title=title,
        description='About the video',
        video_url='https://www.youtube.com/watch?v=abcdefghijk',
    )
    Question.objects.bulk_create(
        Question(quiz=quiz, question_title=f'Question {number + 1}',
                 question_options=['A', 'B', 'C', 'D'], answer='A')
        for number in range(questions)
    )
    return quiz


def quiz_answer(questions=10):
    """A quiz as the pipeline returns it after a successful Gemini call."""
    return {
        'title': 'Elephants',
        'description': 'A short video about elephants.',
        'questions': [
            {
                'question_title': f'Question {number + 1}',
                'question_options': ['A', 'B', 'C', 'D'],
                'answer': 'B',
            }
            for number in range(questions)
        ],
    }
