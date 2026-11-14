# Chatbook

Turn a long WhatsApp, Instagram or Facebook chat into a print-ready PDF that looks like the chat on your phone, with every
photo and video where it was sent. It can also make a photo album from the same export.

It is built for chats that run for months. On the small cloud container it was tested on, a 9,000-message
chat with 90 photos (about 495 pages) is made in under a minute, and a 30,000-message chat with 300
photos (about 1,650 pages) in about two minutes.

* **Frontend:** React 18, Vite, TypeScript, plain CSS (light, dark and phone layouts).
* **Backend:** Python 3.10+, FastAPI, Jinja2, Pillow, Playwright (headless Chromium prints the PDF), pypdf.
* **No database.** Each upload is a "job" in a folder on disk and is deleted automatically.

```
chatbook/
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── api/             REST routes (health, jobs, exports)
│   │   ├── core/            chat parser and data models
│   │   ├── services/        ingest, media, jobs store, export manager
│   │   │   └── render/      layout, plan, HTML view model, Chromium PDF
│   │   ├── templates/       Jinja templates and the print stylesheet
│   │   ├── config.py        settings (CHATBOOK_* environment variables)
│   │   └── main.py          app factory, serves the built frontend
│   ├── tests/               pytest suite (parser, ingest, render, API)
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/                React + Vite app
│   └── src/                 api client, hooks, components, styles, unit tests
├── Dockerfile
└── docker-compose.yml
```

## What it does

* Reads chat exports: WhatsApp `.zip` (chat plus media) or bare `_chat.txt`, and Instagram or Facebook
  "Download your information" JSON exports (`message_1.json` plus media). Supports Android and iPhone
  formats, multi-line messages, system messages, deleted messages, voice notes, documents, stickers.
* Detects day-first or month-first dates and tells you when a chat is ambiguous so you can flip it.
* Merges several exports of the same chat and removes the overlap. Use this when WhatsApp limits
  the size of one export.
* **Chat book:** bubbles, times, sender names in groups, photo and video bubbles with captions,
  cover page, contents page with real page numbers, running header, page numbers, bookmarks.
* **Photo album:** only photos and videos, grouped by month, day or person, 1 to 4 per row.
* A4, Letter, A5 or square; three styles (classic, clean, ink saver); small, medium or large text;
  12 or 24 hour clock.
* Filters: date range, people, search words.
* Splits very long chats into volumes (by month, year or size) downloaded together as a `.zip`.
* Live preview in the browser with an estimated page count before you export.

## Requirements

| Need | Notes |
| --- | --- |
| Python 3.10 or newer | tests pass on 3.10 and 3.13 |
| Node.js 18 or newer | only to build or develop the frontend |
| Chromium for Playwright | installed with one command below, about 150 MB |
| ffmpeg (optional) | gives videos a still frame and a duration. Without it, videos print as a plain tile |

## Run it (production style: one server on port 8000)

### Windows (PowerShell)

```powershell
# 1. Build the frontend once
cd frontend
npm install
npm run build
cd ..

# 2. Backend
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional: install dev/test tools (pytest, httpx, pymupdf, ruff)
pip install -r requirements-dev.txt
python -m playwright install chromium

# 3. Start
python -m uvicorn app.main:app --port 8000
```

Run each command on its own line and check that the prompt starts with `(.venv)`. Using
`python -m ...` makes sure the virtual environment's copies are used.

If PowerShell refuses to run the activate script, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.venv\Scripts\activate.bat` in
Command Prompt.

Open <http://127.0.0.1:8000>. Click **or try a sample chat** to see it work without a real export.

For ffmpeg on Windows: `winget install Gyan.FFmpeg`, then open a new terminal.

### Linux or macOS

```bash
cd frontend && npm install && npm run build && cd ..
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # for tests and development
playwright install chromium          # on Linux also: playwright install-deps chromium
uvicorn app.main:app --port 8000
```

## Develop (hot reload)

Two terminals.

```bash
# backend (from backend/, virtualenv active)
uvicorn app.main:app --reload --port 8000

# frontend (from frontend/)
npm run dev                          # http://localhost:5173, forwards /api to port 8000
```

Checks:

```bash
cd backend  && pytest                # 80+ tests; add  -m "not browser"  to skip the ones that start Chromium
cd frontend && npm test              # unit tests
cd frontend && npm run typecheck
cd frontend && npm run build         # typecheck and production build
```

## Docker

```bash
docker compose up --build            # http://localhost:8000
```

The image uses the official Playwright base image, installs ffmpeg and Noto fonts, builds the
frontend and keeps its working files in the `chatbook-data` volume. The Dockerfile was written
alongside the code but **was not built or run** where this project was produced, so expect to fix a
detail or two on the first build.

## How to export a chat from WhatsApp

Open the chat, tap the contact or group name, choose **Export chat**, then **Include media**.
Save or share the `.zip` to your computer. WhatsApp limits how much one export can hold, so for a
very long chat export in parts (for example by exporting, then clearing older media) and add the parts
together in Chatbook with **Add another export**.

## How to export from Instagram or Facebook

In the Instagram or Facebook app, go to **Settings & privacy → Accounts Centre → Your information and permissions → Download your information**.
1. Choose **Download or transfer information**, pick your account, then select **Some of your information** and check **Messages**.
2. Select **Download to device**.
3. **Important:** Set the Format to **JSON** (not HTML) and Media quality to **High**.
4. When Meta emails you the download link, download the `.zip` and upload it to Chatbook. Chatbook will automatically detect the chat folder and media.

## Settings

All optional, set as environment variables or in `backend/.env` (see `.env.example`).

| Variable | Default | Meaning |
| --- | --- | --- |
| `CHATBOOK_DATA_DIR` | `backend/data` | Where jobs, media and exports live |
| `CHATBOOK_JOB_TTL_HOURS` | `24` | A job and its files are deleted this long after last use |
| `CHATBOOK_CLEANUP_INTERVAL_MINUTES` | `15` | How often expired jobs are swept |
| `CHATBOOK_MAX_UPLOAD_MB` | `4096` | Largest upload (all files of one request) |
| `CHATBOOK_MAX_UNZIPPED_MB` | `8192` | Largest total size an uploaded zip may expand to |
| `CHATBOOK_MAX_SINGLE_MEDIA_MB` | `512` | Larger single files inside a zip are skipped |
| `CHATBOOK_MEDIA_WORKERS` | `4` | Threads that make thumbnails |
| `CHATBOOK_PREVIEW_ITEMS_PER_PAGE` | `250` | Messages shown per preview section |
| `CHATBOOK_CORS_ORIGINS` | the Vite dev origins | Origins allowed to call the API from another port |
| `CHATBOOK_STATIC_DIR` | `frontend/dist` if built | Folder served as the web app |
| `CHATBOOK_CHROMIUM_NO_SANDBOX` | `false` | Needed when running as root, for example in Docker |

## How big a chat can it handle

Measured on the development machine (a small cloud container), text with some photos:

| Chat | Pages | PDF time | Notes |
| --- | --- | --- | --- |
| 3,000 messages, 30 photos | 166 | about 18 s | |
| 9,000 messages, 90 photos | 495 | about 42 s | 73 MB, peak memory about 0.5 GB |
| 30,000 messages, 300 photos | 1,648 | about 2 min | 244 MB, peak memory up to about 1.5 GB. Reading the upload took 17 s. The page estimate said 1,599 |

Chromium slows down sharply when it paginates one very long document, so Chatbook lays out about
100 pages at a time and joins the parts into one PDF. Page numbers, the contents page and bookmarks
carry across the joins. Splitting by month (**Split into volumes**) is still the best way to print a
very long chat: each volume is a book you can bind.

Memory and disk: photos are shrunk once at upload (1000 px for screen, 2000 px for the high
quality print option), so exporting does not reread the originals. Plan on roughly the size of the
export again in free disk space, plus the PDF.

## API

JSON, snake_case, under `/api/v1`. Interactive docs are at `/docs` while the server runs.

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Version, whether ffmpeg and Chromium are available |
| `POST /jobs` | Upload one or more export files (`files`), optional `date_order`. Returns 202 and processes in the background |
| `POST /jobs/sample` | Create a job from a generated sample chat |
| `GET /jobs/{id}` | Job status, progress, senders, counts, date range |
| `POST /jobs/{id}/files` | Add another export to merge |
| `PATCH /jobs/{id}` | Change the date order (`dmy` or `mdy`) and re-read |
| `DELETE /jobs/{id}` | Delete the job and all its files now |
| `GET /jobs/{id}/media/{web or print}/{file}` | Processed media |
| `POST /jobs/{id}/preview` | `{options, volume, page}` returns HTML for the preview plus stats |
| `POST /jobs/{id}/exports` | Start a PDF export with the same `options`. Returns 202 |
| `GET /jobs/{id}/exports/{eid}` | Progress and, when done, the files |
| `DELETE /jobs/{id}/exports/{eid}` | Cancel |
| `GET /jobs/{id}/exports/{eid}/files/{name}` | Download (`?inline=true` to open in the browser) |

## Privacy and security

* Chats are processed on the machine that runs the server. Nothing is sent to a third party.
* Jobs are deleted after 24 hours of inactivity, or at once with the remove button.
* **There is no login.** It is designed for your own computer or a private network. If you host it on
  the internet, put it behind authentication (a reverse proxy with basic auth, or your platform's
  access control) first. Anyone who can reach the server and knows a job id can read that job.
* Uploaded zips are never extracted by path: files are read by name and written under names the
  server picks, so a malicious archive cannot write outside its job folder. Sizes are limited.
* Chromium blocks every network request while printing, so a chat cannot make it fetch anything.
* Run Chromium without `--no-sandbox` where you can. The Docker image sets it because the container
  runs as root; do not expose that container to uploads from people you do not trust.

## Known limits

* Voice notes and audio are drawn as a player bar. The sound is not embedded (a PDF cannot play it).
* Videos print as a still frame with a play mark and duration; the video itself is not embedded.
* WhatsApp does not record who exported the chat, so you pick which person sits on the right.
* Link previews, reactions, replies (quoted messages) and polls are exported by WhatsApp as plain
  text or not at all, so they appear as text.
* The preview is HTML. Final line and page breaks are decided by Chromium when it prints, so
  page numbers in the preview are not shown; the estimate is typically within about 20 percent.
* Fonts: Noto Sans is used when installed, otherwise the system font. Right-to-left text and
  complex scripts print correctly but have only been spot-checked (Devanagari).

## License

Choose one before you share this code. No license file is included.
