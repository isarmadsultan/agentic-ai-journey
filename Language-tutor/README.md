# Language-Tutor

A black-and-green themed language learning workspace with account creation, language enrollment, vocabulary tracking, and story generation.

The project ships with:
- A CLI workflow backed by SQLite.
- A presentable HTML/CSS/JS front end (static, localStorage-based).
- An LLM story generator in the Python flow (optional, via HTTP endpoint).

## Features

- Create accounts and log in.
- Enroll in languages from a curated list.
- Add vocabulary with optional meaning and proficiency tags.
- Generate short stories that reuse your vocabulary.
- Story theme input and vocabulary selection modes (all/manual/auto‑pick) in the web UI.

## Project Structure

- `src/` Python CLI and database logic.
- `Database/` SQLite database folder (created at runtime).
- `web/` Static UI (HTML/CSS/JS).

## Quick Start (Web UI)

Open `web/index.html` directly in a browser, or run a local server:

```powershell
cd "d:\AI agents mastery\Language-tutor"
python -m http.server 8000 --directory web
```

Then open `http://localhost:8000`.

## Quick Start (CLI)

```powershell
cd "d:\AI agents mastery\Language-tutor"
python src\app.py
```

## LLM Story Generation (CLI)

The CLI story generator calls an HTTP endpoint:

- Set `LLM_URL` and `LLM_MODEL` as needed.
- Install `requests` if missing.

```powershell
pip install requests
$env:LLM_URL = "http://127.0.0.1:1235/v1/chat/completions"
$env:LLM_MODEL = "local-model"
python src\story_creation.py
```

## Notes

- The web UI stores data in `localStorage` for now.
- The CLI uses SQLite in `Database/language_learning.db`.

## Roadmap Ideas

- Wire the web UI to the SQLite backend via a small API service.
- Add password hashing with `bcrypt`/`argon2`.
- Add automated tests for DB and story workflows.
