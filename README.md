# Quizly API

REST backend for Quizly. Built with Django and Django REST Framework.

Users paste a YouTube link and get a quiz with ten questions about the
video. The backend downloads the audio, transcribes it locally with Whisper
and lets Gemini write the questions.

The frontend is not part of this repository, see [Frontend](#frontend).

## Requirements

- Python 3.12+
- pip
- FFmpeg, Whisper needs it to read the audio
- Node.js 22+ (or Deno), yt-dlp needs a JavaScript runtime for YouTube
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com)

### Check Python

macOS and Linux:

```bash
python3 --version
```

Windows:

```bash
python --version
```

It has to be 3.12 or higher. If it is older, install a current version from
[python.org](https://www.python.org/downloads/) and open a new terminal.

### Install FFmpeg

macOS (with [Homebrew](https://brew.sh)):

```bash
brew install ffmpeg
```

Windows:

```bash
winget install --id Gyan.FFmpeg -e --source winget
```

Open a new terminal afterwards and check that it is found:

```bash
ffmpeg -version
```

### Install Node.js

macOS:

```bash
brew install node
```

Windows:

```bash
winget install --id OpenJS.NodeJS.LTS -e --source winget
```

Open a new terminal afterwards and check the version, it has to be 22 or
higher:

```bash
node --version
```

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/weskakay/quizly.git
```

**2. Enter the project folder**

```bash
cd quizly
```

**3. Create a virtual environment**

macOS and Linux:

```bash
python3 -m venv .venv
```

Windows:

```bash
python -m venv .venv
```

**4. Activate it**

macOS and Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

**5. Install the dependencies**

```bash
pip install -r requirements.txt
```

**6. Create your .env file**

macOS and Linux:

```bash
cp .env.example .env
```

Windows:

```bash
copy .env.example .env
```

Open `.env` and put your Gemini API key behind `GEMINI_API_KEY`.

**7. Create the database**

```bash
python manage.py migrate
```

**8. Start the server**

```bash
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`.

## Frontend

Keep the API running and serve the frontend on port 5500 or 5501. Open it
via `127.0.0.1`, not `localhost`, otherwise the browser does not send the
login cookies to the API.

## Configuration

All settings are read from `.env`, see `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key | Set your own outside of local development |
| `DJANGO_DEBUG` | `True` | Turn off outside of local development |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma separated host names |
| `JWT_COOKIE_SECURE` | `False` | `True` when the API runs behind HTTPS |
| `GEMINI_API_KEY` | none | Required to generate quizzes |
| `GEMINI_MODEL` | see `.env.example` | Gemini model used for the questions |
| `WHISPER_MODEL` | `base` | Whisper model size, larger is slower but more exact |
| `MAX_VIDEO_MINUTES` | `20` | Longer videos are rejected |

CORS allows the frontend on ports 5500 and 5501, on `localhost` and
`127.0.0.1`, with cookies.

## Development

Install the development tools:

```bash
pip install -r requirements-dev.txt
```

Run the linter:

```bash
flake8
```

Run the tests with coverage:

```bash
coverage run manage.py test
```

```bash
coverage report -m
```
