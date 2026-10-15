from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import yt_dlp
from django.test import SimpleTestCase, override_settings
from google.genai import errors as genai_errors

from quiz_app.tests.helpers import quiz_answer
from quiz_app.utils import (
    QuizGenerationError,
    VideoError,
    check_duration,
    download_audio,
    fetch_video_info,
    generate_quiz_data,
    request_quiz_text,
    transcribe_audio,
    ydl_options,
)

URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


def fake_ydl(**methods):
    """A YoutubeDL stand-in usable as context manager."""
    ydl = MagicMock(**methods)
    ydl.__enter__.return_value = ydl
    return ydl


class VideoTests(SimpleTestCase):
    """Covers reading video info, the length check and the download."""

    @patch('quiz_app.utils.yt_dlp.YoutubeDL')
    def test_info_is_read_without_download(self, youtube_dl):
        youtube_dl.return_value = fake_ydl()
        fetch_video_info(URL)
        youtube_dl.return_value.extract_info.assert_called_once_with(
            URL, download=False
        )

    @patch('quiz_app.utils.yt_dlp.YoutubeDL')
    def test_unavailable_video_raises_video_error(self, youtube_dl):
        error = yt_dlp.utils.DownloadError('private video')
        youtube_dl.return_value = fake_ydl(
            **{'extract_info.side_effect': error}
        )
        for action in (lambda: fetch_video_info(URL),
                       lambda: download_audio(URL, '/tmp')):
            with self.assertRaises(VideoError):
                action()

    @override_settings(MAX_VIDEO_MINUTES=20)
    def test_duration_limit(self):
        check_duration({'duration': 20 * 60})
        for info in ({'duration': 20 * 60 + 1}, {'duration': None}, {}):
            with self.subTest(info=info):
                with self.assertRaises(VideoError):
                    check_duration(info)

    @patch('quiz_app.utils.yt_dlp.YoutubeDL')
    def test_download_returns_file_in_folder(self, youtube_dl):
        youtube_dl.return_value = fake_ydl(
            **{'prepare_filename.return_value': '/tmp/x/id.webm'}
        )
        self.assertEqual(download_audio(URL, '/tmp/x'), '/tmp/x/id.webm')
        options = youtube_dl.call_args.args[0]
        self.assertTrue(options['outtmpl'].startswith('/tmp/x'))
        self.assertTrue(options['noplaylist'])

    def test_options_without_folder_have_no_template(self):
        self.assertNotIn('outtmpl', ydl_options())


class TranscriptionTests(SimpleTestCase):
    """Covers the Whisper step."""

    @patch('quiz_app.utils.whisper.load_model')
    def test_text_is_returned_trimmed(self, load):
        load.return_value.transcribe.return_value = {'text': ' Hello '}
        self.assertEqual(transcribe_audio('a.webm'), 'Hello')

    @patch('quiz_app.utils.whisper.load_model')
    def test_silent_video_raises_video_error(self, load):
        load.return_value.transcribe.return_value = {'text': '  '}
        with self.assertRaises(VideoError):
            transcribe_audio('a.webm')

    @patch('quiz_app.utils.whisper.load_model')
    def test_missing_ffmpeg_raises_generation_error(self, load):
        load.return_value.transcribe.side_effect = FileNotFoundError('ffmpeg')
        with self.assertRaises(QuizGenerationError):
            transcribe_audio('a.webm')

    @override_settings(WHISPER_MODEL='tiny')
    @patch('quiz_app.utils.whisper.load_model')
    def test_configured_whisper_model_is_used(self, load_model):
        load_model.return_value.transcribe.return_value = {'text': 'Hi'}
        transcribe_audio('a.webm')
        load_model.assert_called_once_with('tiny')


class GeminiRequestTests(SimpleTestCase):
    """Covers the single Gemini call."""

    @patch('quiz_app.utils.genai.Client')
    def test_answer_text_is_returned(self, client):
        generate = client.return_value.models.generate_content
        generate.return_value.text = '{"ok": true}'
        self.assertEqual(request_quiz_text('p', 'model-x'), '{"ok": true}')
        self.assertEqual(generate.call_args.kwargs['model'], 'model-x')

    @patch('quiz_app.utils.genai.Client')
    def test_api_and_network_errors_become_generation_errors(self, client):
        errors = [
            genai_errors.ServerError(503, {'error': {'message': 'busy'}}),
            httpx.ReadTimeout('slow'),
            ValueError('missing key'),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                client.return_value.models.generate_content.side_effect = error
                with self.assertRaises(QuizGenerationError):
                    request_quiz_text('p', 'model-x')


class GenerateQuizDataTests(SimpleTestCase):
    """Covers the whole pipeline with every outside call faked."""

    @patch('quiz_app.utils.ask_gemini_for_quiz')
    @patch('quiz_app.utils.transcribe_audio')
    @patch('quiz_app.utils.download_audio')
    @patch('quiz_app.utils.fetch_video_info')
    def test_pipeline_runs_in_order(self, info, download, transcribe, ask):
        info.return_value = {'duration': 60}
        transcribe.return_value = 'Elephants have long trunks.'
        ask.return_value = quiz_answer()
        self.assertEqual(generate_quiz_data(URL), quiz_answer())
        self.assertIn('Elephants have long trunks.', ask.call_args.args[0])

    @patch('quiz_app.utils.transcribe_audio')
    @patch('quiz_app.utils.download_audio')
    @patch('quiz_app.utils.fetch_video_info')
    def test_audio_folder_is_removed_on_error(self, info, download,
                                              transcribe):
        info.return_value = {'duration': 60}
        transcribe.side_effect = QuizGenerationError('whisper failed')
        with self.assertRaises(QuizGenerationError):
            generate_quiz_data(URL)
        folder = download.call_args.args[1]
        self.assertFalse(Path(folder).exists())

    @patch('quiz_app.utils.download_audio')
    @patch('quiz_app.utils.fetch_video_info')
    def test_long_video_is_not_downloaded(self, info, download):
        info.return_value = {'duration': 3 * 60 * 60}
        with self.assertRaises(VideoError):
            generate_quiz_data(URL)
        download.assert_not_called()
