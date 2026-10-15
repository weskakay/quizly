import json
import logging
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

YOUTUBE_HOSTS = {
    'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
    'youtu.be', 'www.youtu.be',
}
VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}')
QUESTION_COUNT = 10
OPTION_COUNT = 4
INVALID_QUESTION = 'Gemini returned an invalid question.'
GEMINI_TIMEOUT_MS = 60_000
GEMINI_CONFIG = types.GenerateContentConfig(
    response_mime_type='application/json'
)
QUIZ_PROMPT = """Based on the following transcript, generate a quiz in valid
JSON format. The quiz must follow this exact structure:
{
  "title": "Create a concise quiz title based on the topic of the
    transcript.",
  "description": "Summarize the transcript in no more than 150 characters.
    Do not include any quiz questions or answers.",
  "questions": [
    {
      "question_title": "The question goes here.",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "The correct answer from the above options"
    }
  ]
}
Requirements:
- Exactly 10 questions.
- Each question must have exactly 4 distinct answer options.
- Only one correct answer is allowed per question, and it must be present
  in 'question_options'.
- Write title, description, questions and options in the language of the
  transcript.
- The output must be valid JSON and parsable as-is (e.g., using Python's
  json.loads).
- Do not include explanations, comments, or any text outside the JSON."""


class VideoError(Exception):
    """The video cannot be used, the user has to pick another one."""


class QuizGenerationError(Exception):
    """Transcription or the AI failed, the user did nothing wrong."""


def normalize_youtube_url(url):
    """Turns any YouTube link into https://www.youtube.com/watch?v=<id>."""
    try:
        parsed = urlparse(url.strip())
    except ValueError as error:
        raise VideoError('Invalid YouTube URL.') from error
    is_youtube = parsed.hostname in YOUTUBE_HOSTS
    if parsed.scheme not in ('http', 'https') or not is_youtube:
        raise VideoError('Invalid YouTube URL.')
    video_id = extract_video_id(parsed)
    if not VIDEO_ID.fullmatch(video_id):
        raise VideoError('Invalid YouTube URL.')
    return f'https://www.youtube.com/watch?v={video_id}'


def extract_video_id(parsed):
    """Finds the video id in watch, youtu.be, shorts, embed or live links."""
    parts = parsed.path.strip('/').split('/')
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        return parts[0]
    if parsed.path == '/watch':
        return parse_qs(parsed.query).get('v', [''])[0]
    if len(parts) == 2 and parts[0] in ('shorts', 'embed', 'live'):
        return parts[1]
    return ''


def ydl_options(folder=None):
    """Options for yt-dlp: best audio only, no playlist, no console output."""
    options = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'noprogress': True,
        'js_runtimes': {'deno': {}, 'node': {}},
    }
    if folder:
        options['outtmpl'] = str(Path(folder) / '%(id)s.%(ext)s')
    return options


def fetch_video_info(url):
    """Reads title and duration without downloading anything."""
    try:
        with yt_dlp.YoutubeDL(ydl_options()) as ydl:
            return ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as error:
        raise VideoError('Video could not be loaded.') from error


def check_duration(info):
    """Rejects live streams and videos above the configured length."""
    duration = info.get('duration')
    limit = settings.MAX_VIDEO_MINUTES
    if not duration:
        raise VideoError('Video could not be loaded.')
    if duration > limit * 60:
        raise VideoError(f'Video is too long (max. {limit} minutes).')


def download_audio(url, folder):
    """Downloads the audio track into folder and returns the file path."""
    try:
        with yt_dlp.YoutubeDL(ydl_options(folder)) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except yt_dlp.utils.DownloadError as error:
        raise VideoError('Video could not be loaded.') from error


def transcribe_audio(path):
    """Turns the audio file into text with Whisper, locally."""
    try:
        model = whisper.load_model(settings.WHISPER_MODEL)
        result = model.transcribe(path, fp16=False)
    except (RuntimeError, OSError) as error:
        raise QuizGenerationError('Transcription failed.') from error
    text = result['text'].strip()
    if not text:
        raise VideoError('The video has no spoken text.')
    return text


def build_prompt(transcript):
    """Puts the transcript under the quiz instructions."""
    return f'{QUIZ_PROMPT}\n\nTranscript:\n{transcript}'


def request_quiz_text(prompt, model):
    """Sends the prompt to one Gemini model and returns its raw answer."""
    try:
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        )
        response = client.models.generate_content(
            model=model, contents=prompt, config=GEMINI_CONFIG,
        )
    except (genai_errors.APIError, httpx.HTTPError, ValueError) as error:
        raise QuizGenerationError(f'{model} request failed.') from error
    return response.text or ''


def strip_code_fences(text):
    """Removes ``` or ```json fences Gemini sometimes puts around JSON."""
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else ''
        text = text.rsplit('```', 1)[0]
    return text.strip()


def clean_question(question):
    """Trims all texts so the answer matches its option exactly."""
    if not isinstance(question, dict):
        raise QuizGenerationError(INVALID_QUESTION)
    options = question.get('question_options')
    if not isinstance(options, list):
        raise QuizGenerationError(INVALID_QUESTION)
    return {
        'question_title': str(question.get('question_title', '')).strip(),
        'question_options': [str(option).strip() for option in options],
        'answer': str(question.get('answer', '')).strip(),
    }


def options_are_valid(options, answer):
    """Four filled, different options and the answer is one of them.

    Used for Gemini answers and for questions edited in the admin.
    """
    if not isinstance(options, list) or len(options) != OPTION_COUNT:
        return False
    texts = [str(option) for option in options]
    if not all(texts) or len(set(texts)) != OPTION_COUNT:
        return False
    return answer in options


def validate_question(question):
    """Checks that a question has a title and playable options."""
    if not question['question_title']:
        raise QuizGenerationError(INVALID_QUESTION)
    if not options_are_valid(question['question_options'],
                             question['answer']):
        raise QuizGenerationError(INVALID_QUESTION)


def load_quiz_json(text):
    """Parses the raw Gemini answer and checks the outer structure."""
    try:
        data = json.loads(strip_code_fences(text))
    except json.JSONDecodeError as error:
        raise QuizGenerationError('Gemini returned no valid JSON.') from error
    questions = data.get('questions') if isinstance(data, dict) else None
    if not isinstance(questions, list):
        raise QuizGenerationError('Gemini returned an invalid quiz.')
    return data


def parse_quiz(text):
    """Turns the Gemini answer into title, description and 10 questions."""
    data = load_quiz_json(text)
    questions = [clean_question(question) for question in data['questions']]
    title = str(data.get('title', '')).strip()
    if len(questions) != QUESTION_COUNT or not title:
        raise QuizGenerationError('Gemini returned an invalid quiz.')
    for question in questions:
        validate_question(question)
    return {
        'title': title[:255],
        'description': str(data.get('description', '')).strip(),
        'questions': questions,
    }


def ask_gemini_for_quiz(prompt):
    """Tries the configured models in order until one returns a valid quiz.

    Free Gemini models are often overloaded (503), the next one usually
    answers.
    """
    last_error = None
    for model in settings.GEMINI_MODELS:
        try:
            return parse_quiz(request_quiz_text(prompt, model))
        except QuizGenerationError as error:
            logger.warning('Gemini model %s failed: %s', model, error)
            last_error = error
    raise last_error or QuizGenerationError('No Gemini model configured.')


def generate_quiz_data(url):
    """Runs the whole pipeline: length check, audio, transcript, quiz.

    The audio only lives in a temporary folder that is removed afterwards,
    also when something fails.
    """
    check_duration(fetch_video_info(url))
    with tempfile.TemporaryDirectory() as folder:
        transcript = transcribe_audio(download_audio(url, folder))
    return ask_gemini_for_quiz(build_prompt(transcript))
