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
On macOS Homebrew works as well:

```bash
brew install python@3.12
```

Then use `python3.12` instead of `python3` in setup step 3.

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

Then create a secret key, it also signs the login tokens:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Put the output behind `DJANGO_SECRET_KEY` in `.env`.

**7. Create the database**

```bash
python manage.py migrate
```

**8. Start the server**

```bash
python manage.py runserver
```

The API runs at `http://127.0.0.1:8000/api/`.

The first quiz takes a bit longer: Whisper downloads its model (about
140 MB) once.

## Frontend

Tested with the frontend as of commit `ae8e863` (February 2026). Its
`config.js` needs no change, the default `API_BASE_URL` already points to
`http://127.0.0.1:8000/api/`.

The frontend uses absolute paths, so serve its root folder, for example with
the Live Server extension of VS Code or from inside the frontend folder:

macOS and Linux:

```bash
python3 -m http.server 5501
```

Windows:

```bash
python -m http.server 5501
```

Open `http://127.0.0.1:5501`, not `localhost`, otherwise the browser does not
send the login cookies to the API. There are no guest accounts, register a
user first. The frontend itself asks for a password with a lowercase and an
uppercase letter, a digit and at least six characters.

## Authentication

Login sets two HttpOnly cookies, the frontend never sees the tokens:

| Cookie | Lifetime | Used for |
|---|---|---|
| `access_token` | 5 minutes | every protected request |
| `refresh_token` | 1 day | token refresh and logout |

The browser sends both cookies along with every request. When the access
token expires, the frontend calls the refresh endpoint and repeats the
request. Logout puts the refresh token on the blacklist and deletes both
cookies.

## Endpoints

Login uses the username, not the email address. Other methods, for example
PUT on a quiz, return 405.

### Auth

| Method | Path | Who | Codes |
|---|---|---|---|
| POST | `/api/register/` | anyone | 201, 400 |
| POST | `/api/login/` | anyone | 200, 401 |
| POST | `/api/logout/` | logged in users | 200, 401 |
| POST | `/api/token/refresh/` | refresh cookie | 200, 401 |

Registration takes `username`, `email`, `password` and `confirmed_password`.
Usernames and email addresses must be unique, the email check ignores case.
Wrong login data returns the same general message for an unknown user and a
wrong password.

### Quizzes

| Method | Path | Who | Codes |
|---|---|---|---|
| GET | `/api/quizzes/` | logged in users, own quizzes only | 200, 401 |
| POST | `/api/quizzes/` | logged in users | 201, 400, 401, 500 |
| GET | `/api/quizzes/{id}/` | owner only | 200, 401, 403, 404 |
| PATCH | `/api/quizzes/{id}/` | owner only | 200, 400, 401, 403, 404 |
| DELETE | `/api/quizzes/{id}/` | owner only | 204, 401, 403, 404 |

A quiz is created from `{"url": "<youtube link>"}`. Watch, short, embed,
live and `youtu.be` links are accepted and stored as
`https://www.youtube.com/watch?v=<id>`. Every quiz has ten questions with
four options each, the answer is always one of the options. The list returns
the newest quiz first. A PATCH changes `title` and `description`, other
fields are ignored. Deleting a quiz deletes its questions.

## Design decisions

- **Quiz creation runs synchronously.** The POST downloads the audio,
  transcribes it and asks Gemini before it answers, usually within a
  minute. The frontend shows a loading overlay meanwhile, so a task queue
  would only add Redis and a worker without a visible benefit.
- **400 or 500 for a failed quiz.** Everything the user can fix returns 400
  with a message: a link that is no YouTube video, a private, removed or
  live video, a video longer than 20 minutes or one without speech. When
  Whisper or Gemini fail, the API returns 500 with a general message and
  logs the cause. Videos are checked for their length before anything is
  downloaded, the audio only lives in a temporary folder that is always
  removed.
- **Quizzes in the language of the video.** The prompt asks Gemini to write
  title, description, questions and options in the language of the
  transcript, so a German video gives a German quiz.
- **Several Gemini models.** The free Flash models are often overloaded and
  answer 503. `GEMINI_MODELS` lists models that are tried in order, each
  with a 60 second timeout. An answer that is no valid quiz also moves on to
  the next model.
- **Current yt-dlp.** YouTube changes often. Since late 2025 yt-dlp needs a
  JavaScript runtime for YouTube, older versions such as 2025.07.21 fail to
  load videos. The project therefore uses a current release together with
  Node.js or Deno.
- **No CSRF token.** The frontend sends no CSRF token. The cookies are
  `SameSite=Lax`, so browsers do not send them along with requests from
  other sites, and CORS only allows the frontend origins.
- **Access token after logout.** Only refresh tokens can be blacklisted. An
  access token stays valid until it expires, at most five minutes, which is
  why its lifetime is short. The browser deletes the cookie on logout.
- **403 for quizzes of other users.** The specification asks for 403. The
  frontend treats 403 like an expired login and moves to the login page,
  this is frontend behaviour.
- **No password rules on registration.** The API checks that both passwords
  match and that username and email are free. The frontend has its own
  password rule. On a failed registration the frontend only shows the
  `username` error, other field errors such as a taken email appear there as
  "undefined", the API response itself names the field.

## Project layout

```
core/       project settings and root urls
auth_app/   registration, login, logout, token refresh, cookie authentication
quiz_app/   quizzes, questions and the pipeline in utils.py
```

Each app keeps its API code in an `api/` folder and its tests in a `tests/`
folder. The tests never call YouTube, Whisper or Gemini, those calls are
faked.

## Admin

Create a staff account:

```bash
python manage.py createsuperuser
```

The admin runs at `http://127.0.0.1:8000/admin/`. A quiz shows its questions
right on its page, single questions can also be edited in their own list.
Questions need exactly four different options and an answer that is one of
them.

## Configuration

All settings are read from `.env`, see `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key | Set your own outside of local development |
| `DJANGO_DEBUG` | `True` | Turn off outside of local development |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma separated host names |
| `JWT_COOKIE_SECURE` | `False` | `True` when the API runs behind HTTPS |
| `GEMINI_API_KEY` | none | Required to generate quizzes |
| `GEMINI_MODELS` | see `.env.example` | Gemini models, tried in order when one is overloaded |
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

Run the tests:

```bash
coverage run manage.py test
```

Show the coverage report:

```bash
coverage report
```
