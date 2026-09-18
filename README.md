# All-in-One Local File Converter

A fast, private, open-source file converter that runs **entirely on your machine**. No network calls, no API keys, no accounts, CPU-only. Drop a file in the browser, get the converted file back in seconds.

Twelve conversions across PDFs, documents, ebooks, and images — behind a single-page React UI and a small FastAPI backend.

```
┌─────────────────────────────────────────────────────────┐
│                Universal Converter                      │
│                                                         │
│              📄  Drop a file here                       │
│                    or click                             │
│                                                         │
│         Detected: PDF                                   │
│         Convert to  [ DOCX ]  [ TXT ]  [ Markdown ]     │
│                                                         │
│                    [  Convert  ]                        │
└─────────────────────────────────────────────────────────┘
```

## Table of contents

- [Supported conversions](#supported-conversions)
- [Design principles](#design-principles)
- [Quick start](#quick-start)
- [Installation](#installation)
- [Running the app](#running-the-app)
- [Using it](#using-it)
- [API reference](#api-reference)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Testing](#testing)
- [Development](#development)
- [Performance notes](#performance-notes)
- [Security](#security)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [License](#license)

## Supported conversions

Twelve flows, each with a direct engine — no universal intermediate representation.

| From      | To      | Engine                    | Notes                                       |
| --------- | ------- | ------------------------- | ------------------------------------------- |
| PDF       | TXT     | PyMuPDF                   | Fastest path; sorted by reading order       |
| PDF       | MD      | PyMuPDF4LLM               | Headings, paragraphs, lists, tables         |
| PDF       | DOCX    | PyMuPDF + python-docx     | Structural (paragraphs, headings, tables, inline images) — not pixel-perfect |
| PDF[]     | PDF     | PyMuPDF (`insert_pdf`)    | Merge in any order, drag to reorder in UI   |
| TXT       | PDF     | ReportLab (bundled Noto)  | A4/Letter, portrait/landscape, font size, margins |
| MD        | PDF     | Pandoc + Typst            | Configurable page size                      |
| DOCX      | PDF     | LibreOffice headless      | Isolated per-request profile                |
| PNG       | JPEG    | Pillow                    | Quality 60–100, transparent alpha composite over configurable background |
| SVG       | JPEG    | resvg + Pillow            | Width/height/scale, background, quality     |
| EPUB      | TXT     | Pandoc                    | Preserves spine order and Unicode           |
| EPUB      | Markdown| Pandoc (GFM, `--wrap=none`) | Headings, lists, links, code, tables      |
| EPUB      | PDF     | Pandoc + Typst            | Reflowable → fixed layout                   |

## Design principles

The whole project has one thesis: **be a converter, not a document-intelligence platform**.

- **Local only.** No cloud calls, no API keys, no telemetry. All processing happens on the machine the app is running on.
- **Shortest direct path.** Every pair has one engine chosen for that pair. There is no universal AST or intermediate representation — the code path from upload to download is short and easy to follow.
- **Small dependency tree.** Eight Python packages, four optional native binaries. All twelve flows work with that set; nothing more is required.
- **Graceful degradation.** The app boots even if every native tool is missing. `/api/system` reports what's available, and the frontend disables conversions whose dependencies aren't installed with a message telling the user which tool to install.
- **No persistent storage.** Every request gets a fresh `TemporaryDirectory` that's deleted after the response streams back. Nothing is kept, nothing is indexed, nothing is logged beyond errors.
- **Not overengineered.** No queues, no databases, no worker processes, no auth, no user model, no microservices. One FastAPI process, one React frontend.

## Quick start

```bash
# 1. Clone
git clone https://github.com/rebuilt-ai-poc/aio-converter.git
cd aio-converter

# 2. Backend (Python 3.12+, uses uv)
cd backend
uv sync
uv run uvicorn app.main:app --port 8000

# 3. Frontend (Node 20+, in a separate terminal)
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

That gets you the eight conversions that don't need external tools. For the other four, follow [Installation](#installation) below.

## Installation

### Prerequisites

- **Python 3.12+** — [uv](https://github.com/astral-sh/uv) is recommended (`uv sync` handles both the interpreter and packages)
- **Node 20+** for the frontend

### Python packages

Handled automatically by `uv sync` (or `pip install -r backend/requirements.txt`):

```
fastapi                    # HTTP framework
uvicorn[standard]          # ASGI server
python-multipart           # multipart/form-data upload parsing
pymupdf                    # PDF text/image/table extraction
pymupdf4llm                # PDF → Markdown
python-docx                # DOCX writing (for PDF → DOCX)
reportlab                  # TXT → PDF
Pillow                     # PNG / JPEG / image compositing
```

### Native tools

Four external binaries power the conversions Pandoc and LibreOffice do best:

| Tool           | Needed for                                    | Approx. install size |
| -------------- | --------------------------------------------- | -------------------- |
| **Pandoc**     | MD → PDF, EPUB → TXT/MD/PDF                   | ~150 MB              |
| **Typst**      | MD → PDF, EPUB → PDF (PDF engine for Pandoc)  | ~30 MB               |
| **LibreOffice**| DOCX → PDF                                    | ~1 GB                |
| **resvg**      | SVG → JPEG                                    | ~5 MB                |

The app runs with any subset of these installed. Use `python scripts/check_dependencies.py` any time to see what's available.

#### Windows

```powershell
winget install --id JohnMacFarlane.Pandoc
winget install --id Typst.Typst
winget install --id TheDocumentFoundation.LibreOffice

# resvg has no winget package. Download resvg-win64.zip from
#   https://github.com/linebender/resvg/releases (last Windows binary: v0.47.0)
# and place resvg.exe on your PATH (e.g. %USERPROFILE%\.local\bin).
```

If a winget package fails to extract (occasionally happens for Typst), download the release archive directly from the vendor's GitHub Releases page — Typst ships a `typst-x86_64-pc-windows-msvc.zip`.

**Pandoc PATH gotcha (Windows):** winget installs Pandoc to `%LOCALAPPDATA%\Pandoc`, which is not automatically added to `PATH`. Add it manually or the app will report `pandoc: false`:

```powershell
setx PATH "%PATH%;%LOCALAPPDATA%\Pandoc"
# Open a new terminal for the change to take effect.
```

#### macOS

```bash
brew install pandoc typst
brew install --cask libreoffice

# resvg — download resvg-macos-*.zip from
#   https://github.com/linebender/resvg/releases
# and place resvg on your PATH.
```

#### Linux (Debian/Ubuntu)

```bash
sudo apt-get install pandoc libreoffice
# Typst — either build from source or grab a release tarball:
#   https://github.com/typst/typst/releases   (typst-x86_64-unknown-linux-musl.tar.xz)
# resvg — https://github.com/linebender/resvg/releases   (resvg-linux-x86_64.tar.gz)
```

### Verify

```bash
python scripts/check_dependencies.py
```

Prints a per-engine ✓/✗ table with actionable install hints for anything missing. When all four native tools are installed, you should see `12 / 12 conversions available`.

## Running the app

### Development (two processes, hot reload)

```bash
# terminal 1 — backend on :8000
cd backend
uv run uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend on :5173, proxies /api → :8000
cd frontend
npm run dev
```

Open http://localhost:5173.

### Production / single-app local

Build the React bundle and let FastAPI serve it as a static SPA:

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn app.main:app --port 8000
# open http://localhost:8000
```

`app/main.py` auto-mounts `frontend/dist/` at `/` with SPA fallback (any non-`/api` GET returns `index.html` if the exact file doesn't exist).

## Using it

- **Drop** or **click to upload** a single file into the drop zone.
- The source format is auto-detected from the file extension **and** its magic bytes — the browser's advertised MIME type is not trusted.
- Only the valid target formats for the detected source appear as chips.
- If a required native tool is missing, the corresponding chip is disabled and a hint tells you what to install.
- Optional conversion settings (page size, quality, background colour, margins, font size, orientation) appear only for pairs that support them.
- Drop **multiple PDFs** to trigger the merge flow — reorder with ↑/↓ or drag, remove individual files with ×, then Merge.
- Success shows the output filename, size, and a Download button. Convert Another resets the UI.

## API reference

Four endpoints. Everything is multipart or JSON — no auth, no cookies, no sessions.

### `GET /api/health`

Liveness probe.

```json
{ "status": "ok" }
```

### `GET /api/system`

Report installed engines, per-pair availability, and upload limits. The frontend calls this on mount to know which chips to disable.

```json
{
  "engines": {
    "pymupdf": true, "pymupdf4llm": true, "python_docx": true,
    "reportlab": true, "pillow": true,
    "pandoc": true, "typst": true, "libreoffice": true, "resvg": true
  },
  "conversions": {
    "pdf->txt": true, "pdf->md": true, "pdf->docx": true,
    "txt->pdf": true, "md->pdf": true, "docx->pdf": true,
    "png->jpg": true, "svg->jpg": true,
    "epub->txt": true, "epub->md": true, "epub->pdf": true,
    "pdf[]->pdf": true
  },
  "limits": { "max_file_mb": 100, "max_merge_files": 50, "max_merge_total_mb": 500 }
}
```

### `POST /api/convert`

Convert a single file. `multipart/form-data`:

| Field           | Required | Description                                     |
| --------------- | -------- | ----------------------------------------------- |
| `file`          | yes      | The uploaded file (streamed to disk)            |
| `output_format` | yes      | One of `pdf`, `txt`, `md`, `docx`, `jpg`        |
| `options`       | no       | JSON object with pair-specific settings         |

Response: the converted file with `Content-Type` set to the target's MIME type and `Content-Disposition: attachment; filename="<original-stem>.<ext>"`.

Options per pair:

| Pair              | Option keys                                                                          |
| ----------------- | ------------------------------------------------------------------------------------ |
| `png→jpg`, `svg→jpg` | `quality` (60–100, default 90), `background` (`"white"`, `"black"`, or `"#RRGGBB"`) |
| `svg→jpg`         | `width`, `height` (pixels), `scale` (float)                                          |
| `txt→pdf`         | `page_size` (`a4`/`letter`), `orientation` (`portrait`/`landscape`), `margins` (`normal`/`narrow`), `font_size` (8–24) |
| `md→pdf`, `epub→pdf` | `page_size` (`a4`/`letter`)                                                      |
| `pdf→txt`         | `preserve_page_breaks` (bool) — inserts `\f` between pages                           |

Example:

```bash
curl -F "file=@report.pdf" -F "output_format=docx" \
     http://localhost:8000/api/convert -o report.docx

curl -F "file=@photo.png" -F "output_format=jpg" \
     -F 'options={"quality":85,"background":"#f0f0f0"}' \
     http://localhost:8000/api/convert -o photo.jpg
```

### `POST /api/merge/pdf`

Merge two or more PDFs in submitted order.

| Field   | Required | Description                     |
| ------- | -------- | ------------------------------- |
| `files` | yes      | Repeat once per PDF, in order  |

Response: `application/pdf` named `merged.pdf`.

```bash
curl -F "files=@ch1.pdf" -F "files=@ch2.pdf" -F "files=@ch3.pdf" \
     http://localhost:8000/api/merge/pdf -o merged.pdf
```

### Error format

Any converter error is returned as JSON with a stable code:

```json
{ "error": { "code": "DEPENDENCY_MISSING", "message": "LibreOffice (soffice) is required for DOCX -> PDF conversion" } }
```

| Code                  | HTTP | Meaning                                              |
| --------------------- | ---- | ---------------------------------------------------- |
| `UNSUPPORTED_FORMAT`  | 400  | Source or target format not in the registry          |
| `INVALID_FILE`        | 400  | Magic bytes don't match extension, or file is empty  |
| `FILE_TOO_LARGE`      | 413  | Size cap exceeded                                    |
| `DEPENDENCY_MISSING`  | 503  | A required native tool isn't installed               |
| `CONVERSION_FAILED`   | 500  | Underlying engine returned an error                  |
| `CONVERSION_TIMEOUT`  | 504  | Subprocess exceeded its per-operation timeout        |

Server logs get the full traceback; clients never see internal detail.

## Architecture

```
Browser
   │
   │ multipart/form-data
   ▼
React / Vite (single page)
   │
   │ POST /api/convert  or  /api/merge/pdf
   ▼
FastAPI  ─►  file validation (extension + magic bytes)
         ─►  streaming upload → per-request TemporaryDirectory
         ─►  registry lookup (source, target) → converter fn
         ─►  converter runs (native Python or subprocess)
         ─►  FileResponse streams result back
         ─►  BackgroundTask deletes the temp dir
```

**One backend, one frontend.** No queue, no worker, no database, no cache. A single Uvicorn process handles every request end to end, delegating blocking work through FastAPI's thread pool when needed.

**Layout** (mirroring the spec's §4 exactly):

```
backend/
  app/
    main.py                    # FastAPI app entry, SPA mount
    api/routes.py              # /health /system /convert /merge/pdf
    converters/
      __init__.py              # CONVERSIONS registry (source, target) → fn
      pdf.py                   # PDF-source flows + PDF merge
      documents.py             # TXT/MD/DOCX/EPUB → PDF via ReportLab / Pandoc / LibreOffice
      images.py                # PNG/SVG → JPEG via Pillow / resvg
    core/
      config.py                # limits, timeouts, asset paths
      files.py                 # streaming upload, output naming
      validation.py            # format detection (ext + magic bytes)
      errors.py                # domain exception hierarchy
    utils/subprocess.py        # safe subprocess wrapper (argv-only, timeout, kill)
    assets/fonts/              # bundled Noto Sans (Regular + Bold)
  tests/
    fixtures/generate.py       # builds all fixtures deterministically (incl. hand-built EPUBs)
    test_pdf.py test_documents.py test_images.py test_api.py
  pyproject.toml               # uv-managed
frontend/
  src/
    api/converter.ts           # single API client
    components/                # DropZone, MergeList, OptionsPanel
    types/                     # SourceFormat, TargetFormat, SystemInfo
    App.tsx                    # single-page converter
scripts/
  check_dependencies.py        # ✓/✗ table + per-OS install hints
  install.md
```

**Adding a new conversion** is:

1. A function `(input_path, output_path, options) -> None` in the appropriate `converters/*.py`.
2. One entry in `CONVERSIONS` in `converters/__init__.py`.
3. One line in `TARGETS_BY_SOURCE` in `frontend/src/App.tsx`.
4. (If gated) one branch in `_pair_available` in `api/routes.py` and one row in `scripts/check_dependencies.py`.

## Configuration

Everything has sensible defaults. Override via environment variables when starting the backend:

| Env var                 | Default | Purpose                                            |
| ----------------------- | ------- | -------------------------------------------------- |
| `MAX_FILE_SIZE_MB`      | 100     | Per-file upload cap                                |
| `MAX_MERGE_FILES`       | 50      | Max number of PDFs in a single merge request       |
| `MAX_MERGE_TOTAL_MB`    | 500     | Combined size cap for a merge upload               |
| `TIMEOUT_IMAGE`         | 30      | Seconds for image subprocesses (resvg)             |
| `TIMEOUT_DOCUMENT`      | 120     | Seconds for document subprocesses (Pandoc)         |
| `TIMEOUT_LARGE_PDF`     | 300     | Seconds for heavy PDF work (LibreOffice)           |

## Testing

```bash
cd backend
uv run pytest
```

Every converter has structural tests, and every API endpoint has a round-trip test via FastAPI's `TestClient`. Tests build their own fixtures programmatically (`tests/fixtures/generate.py`) — no huge binary files in git.

- Fixtures include a plain PDF, a headings PDF, a table PDF, two multi-page PDFs (for merge), a DOCX, a simple Markdown file, plain and Unicode text, opaque/transparent PNGs, simple/transparent SVGs, and two hand-built EPUB 3 archives (built with `zipfile` — no `ebooklib` dependency).
- Tests that need Pandoc, Typst, LibreOffice, or resvg auto-skip with `pytest.mark.skipif` when the binary isn't found. With all four installed, the full suite is 37 tests and takes about 5 seconds.
- CI runs Python tests + frontend type-check/build on Ubuntu (see `.github/workflows/ci.yml`). Native integration tests skip in CI because the tools aren't installed there by default.

## Development

The frontend is TypeScript + Tailwind — `npm run build` type-checks then bundles. The bundle is small (~50 KB gzipped).

- One API client module (`src/api/converter.ts`) — no scattered `fetch` calls.
- Blob URLs are revoked on unmount / reset to avoid leaking memory.
- The DropZone accepts `.pdf,.txt,.md,.markdown,.docx,.png,.svg,.epub`; backend validation is still authoritative.

To add a new format target, keep changes local to one file per layer (registry, validation, UI list, dep checker). Don't introduce interfaces / factories / repositories — the plan explicitly forbids that scaffolding for a converter this size.

## Performance notes

- **PDF → TXT** uses `page.get_text("text", sort=True)`. It does not use the `dict`/`rawdict` trees or render pages. On typical office PDFs it runs at hundreds of pages per second.
- **PDF → Markdown** delegates to PyMuPDF4LLM with `write_images=False` and `embed_images=False`. Falls back to plain-text extraction if PyMuPDF4LLM raises — a conversion never fails just because of an optional-dependency edge case.
- **PDF merge** uses `insert_pdf(...)` — pages are copied at the object level, never re-rendered. `garbage=3, deflate=True` at save time keeps output reasonable without expensive optimization passes.
- **Image conversions** stay entirely in Pillow. Alpha channels are composited over the configured background before JPEG encoding (JPEG has no alpha).
- **SVG → JPEG** shells out to native `resvg` for the rasterization, then Pillow encodes JPEG. Pure Python SVG rendering is intentionally avoided.
- **DOCX → PDF** spins up LibreOffice with a per-request `-env:UserInstallation=file:///<uuid>` profile, so parallel requests can't collide on the profile lock.
- **Heavy Python libraries** (`pymupdf4llm`, `docx`, `reportlab`, `pymupdf`) are imported lazily inside the converter that needs them. `uvicorn app.main:app` boots in a fraction of a second because it doesn't import them at module scope.
- Observed on a mid-range Windows laptop: 6 MB / 44-page EPUB → 6.1 MB PDF in ~1.2 s via HTTP.

## Security

Even for a local app, the code follows the obvious rules:

- **No `shell=True`** anywhere. Subprocesses always take `argv` arrays.
- **User-supplied content never becomes a subprocess argument.** Pandoc filters and Lua scripts are not exposed — the converter chooses every flag itself.
- **Path traversal blocked.** Output filenames are stripped to a safe stem (`[A-Za-z0-9._-]+`) before use. Uploads land in a random `TemporaryDirectory` under `%TEMP%`/`/tmp` with random internal names.
- **Uploaded files are never executed.** Format detection uses extension + magic bytes; the browser MIME type is ignored.
- **Subprocess timeouts.** Every native call has a per-operation timeout and the child process is killed on expiry.
- **Nothing is persisted.** Per-request temp dirs are removed by a FastAPI `BackgroundTask` after the response streams back. No cache, no history, no telemetry.
- **CORS** is scoped to `localhost:5173` (dev only). In single-process production deployment the frontend and backend share an origin.

## Limitations

- **PDF → DOCX is structural, not pixel-perfect.** PDF is a fixed-layout format, DOCX is flow-based. Paragraphs, headings, bold/italic, inline images and simple tables come through cleanly; multi-column magazine layouts, floating text boxes, absolute positioning and unusual typography do not.
- **Scanned PDFs.** OCR is intentionally not included in V1. If PDF → TXT sees no extractable text, it returns a note saying the file may be scanned.
- **CJK / emoji in TXT → PDF.** The bundled Noto Sans covers Latin (extended), Greek and Cyrillic. Chinese/Japanese/Korean and emoji glyphs need additional fonts and will render as blanks with the bundled font alone.
- **EPUB → *.** Delegated to Pandoc. EPUB is reflowable, PDF is fixed pages — the goal is a clean readable rendering, not a pixel-match of an ebook reader. V1 does not extract embedded images (Markdown output is a single `.md` without a media folder). Rich EPUBs with custom `<div class>` wrappers may keep some raw HTML in the Markdown output because there's no clean GFM equivalent.
- **DOCX → PDF** requires LibreOffice. **Markdown → PDF** and **EPUB → \*** require Pandoc (and Typst for the PDF outputs). **SVG → JPEG** requires resvg. Missing binaries disable only the affected conversion; everything else keeps working.

## Roadmap

Nothing here is scheduled — the architecture just makes them straightforward additions.

- **OCR fallback** for scanned PDFs (Tesseract only on pages with no extractable text)
- **Extra image formats:** JPEG → PNG, WEBP → JPEG, HEIC → JPEG, PDF → PNG/JPEG
- **DOCX → TXT / Markdown**, **Markdown → DOCX**, **TXT → DOCX**
- **HTML → PDF / DOCX**
- **PDF utilities:** split, rotate, page extraction, compression
- **EPUB image extraction** (Pandoc `--extract-media` → zip response)
- **Bundled CJK font** for TXT → PDF

## License

MIT — see [LICENSE](LICENSE). Bundled Noto Sans fonts are licensed under the [SIL Open Font License 1.1](https://scripts.sil.org/OFL) by the Noto Project Authors.
