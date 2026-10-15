from django.test import SimpleTestCase

from quiz_app.utils import VideoError, normalize_youtube_url

EXPECTED = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
VALID_LINKS = [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s',
    'https://m.youtube.com/watch?list=PL1&v=dQw4w9WgXcQ',
    'http://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtu.be/dQw4w9WgXcQ?si=abc',
    'https://www.youtube.com/shorts/dQw4w9WgXcQ',
    'https://www.youtube.com/embed/dQw4w9WgXcQ',
    'https://www.youtube.com/live/dQw4w9WgXcQ',
    '  https://youtu.be/dQw4w9WgXcQ  ',
]

INVALID_LINKS = [
    '',
    'dQw4w9WgXcQ',
    'https://vimeo.com/123456',
    'https://evilyoutube.com/watch?v=dQw4w9WgXcQ',
    'javascript:alert(1)',
    'https://www.youtube.com/watch?v=short',
    'https://www.youtube.com/channel/UC1234567890',
    'https://www.youtube.com/playlist?list=PL1',
    'ftp://youtu.be/dQw4w9WgXcQ',
    'http://[::1',
    'https://evilyoutu.be/dQw4w9WgXcQ',
]


class NormalizeYoutubeUrlTests(SimpleTestCase):
    """Covers turning any YouTube link into the watch?v= form."""

    def test_known_link_forms_are_normalized(self):
        for link in VALID_LINKS:
            with self.subTest(link=link):
                self.assertEqual(normalize_youtube_url(link), EXPECTED)

    def test_other_links_are_rejected(self):
        for link in INVALID_LINKS:
            with self.subTest(link=link):
                with self.assertRaises(VideoError):
                    normalize_youtube_url(link)
