# All-in-One Local File Converter

Fast, local, private file conversion. Everything runs on your machine — no
network calls, no API keys, no accounts, CPU-only. Drop a file in the browser
and get the converted file back immediately.

## Supported conversions

| From    | To     | Engine                     |
| ------- | ------ | -------------------------- |
| PDF     | TXT    | PyMuPDF                    |
| PDF     | MD     | PyMuPDF4LLM                |
| PDF     | DOCX   | PyMuPDF + python-docx      |
| PDF[]   | PDF    | PyMuPDF (`insert_pdf`)     |
| TXT     | PDF    | ReportLab (bundled Noto)   |
| MD      | PDF    | Pandoc + Typst             |
| DOCX    | PDF    | LibreOffice headless       |
| PNG     | JPEG   | Pillow                     |
| SVG     | JPEG   | resvg + Pillow             |

## Quick start

```bash
# backend
cd backend
uv sync
uv run uvicorn app.main:app --port 8000

# frontend (dev)
cd frontend
npm install
npm run dev            # http://localhost:5173  (proxies /api to :8000)
```

For a single-app local install, build the frontend and let FastAPI serve it:

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn app.main:app --port 8000
# open http://localhost:8000
```

## Installation

See [`scripts/install.md`](scripts/install.md) for per-OS setup of the four
native tools (Pandoc, Typst, LibreOffice, resvg). To check what's ready:

```bash
python scripts/check_dependencies.py
```

The app runs with any subset of the native tools installed; the frontend
disables conversions whose dependencies are missing and tells you which one
to install.

## Architecture

```
Browser  ──►  React/Vite  ──►  FastAPI  ──►  Format router  ──►  converter
                                                             │
                                                             ├── PDF engine (PyMuPDF)
                                                             ├── Document engine (ReportLab, Pandoc+Typst, LibreOffice)
                                                             └── Image engine (Pillow, resvg)
```

- One FastAPI backend, one React frontend, no database, no queue, no workers.
- Every request gets a private `tempfile.TemporaryDirectory()`. Nothing is
  persisted after the response is streamed back.
- Subprocesses have per-operation timeouts (30 s image, 120 s document,
  300 s large PDF) and are killed on expiry.
- The API surface is tiny:

| Method | Path              | Purpose                                   |
| ------ | ----------------- | ----------------------------------------- |
| GET    | `/api/health`     | Liveness                                  |
| GET    | `/api/system`     | Per-engine availability + limits          |
| POST   | `/api/convert`    | Single-file conversion (multipart)        |
| POST   | `/api/merge/pdf`  | Merge multiple PDFs in submitted order    |

## Performance philosophy

Shortest direct path per format; no universal intermediate representation.
- PDF → TXT uses `page.get_text("text", sort=True)`, not the dict/rawdict trees.
- PDF → MD delegates to PyMuPDF4LLM and skips image extraction by default.
- PDF merge uses `insert_pdf` — no page re-rendering.
- Image conversions stay in Pillow; SVG shells out to native `resvg`.
- Heavy libraries (`pymupdf4llm`, `pymupdf`, `docx`, `reportlab`) are imported
  lazily inside the converter that needs them, so the app boots fast.

## Limitations

- **PDF → DOCX** is structural, not pixel-perfect. PDF is a fixed-layout
  format; DOCX is flow-based. Paragraphs, headings, bold/italic, inline
  images, and simple tables are preserved; complex magazine layouts,
  floating boxes, absolute positioning, and unusual typography are not.
- **Scanned PDFs** need OCR, which V1 does not include. If PDF → TXT sees
  no extractable text, it returns a note saying so.
- **CJK / emoji in TXT → PDF** need a CJK/emoji font. The bundled Noto Sans
  covers Latin (extended), Greek, and Cyrillic. Missing glyphs become blanks.
- **DOCX → PDF** requires LibreOffice. **Markdown → PDF** requires Pandoc
  and Typst. **SVG → JPEG** requires resvg. Missing binaries disable the
  respective conversion in the UI.

## Tests

```bash
cd backend
uv run pytest
```

Every converter has a round-trip or structural test. Integration tests that
need Pandoc/Typst/LibreOffice are auto-skipped when the binary isn't present.

## License

MIT — see [`LICENSE`](LICENSE).
