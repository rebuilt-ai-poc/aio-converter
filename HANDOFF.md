# Handoff — 2026-09-17

## Where things stand

All **12 conversions** implemented (9 original + EPUB → {TXT, MD, PDF}) plus
**4 PDF page-operations** (Split, Delete pages, Extract pages, Reorder pages).
Backend: 69/69 pytest pass. Frontend: `npm run build` clean.
Dependency checker (`GET /api/system`) reports **12/12** conversions plus
**4/4** page operations (`pdf:split`, `pdf:delete-pages`,
`pdf:extract-pages`, `pdf:reorder-pages`) — all gated on PyMuPDF only.

The four page-ops share one PyMuPDF engine in `backend/app/converters/pdf.py`
and one frontend shell (`components/PdfToolLayout.tsx`) — each SEO-routed page
under `frontend/src/pages/` is a thin wrapper (30–110 lines).

## Environment notes for the next session

- Python: **`uv` with CPython 3.12.13**. `py -3.12` is not registered as a
  standard launcher entry — use `uv run python …` or activate `.venv`.
- **Pandoc lives at `C:\Users\Aditya\AppData\Local\Pandoc`** (winget's default
  per-user location). It is NOT on the system PATH after install; prepend it
  for every terminal session, or add it to PATH permanently:
  `export PATH="/c/Users/Aditya/AppData/Local/Pandoc:$PATH"`.
  `shutil.which("pandoc")` inside a uvicorn started with this PATH resolves
  fine; without it, `/api/system` will report `pandoc: false`.
- **resvg** is at `C:\Users\Aditya\.local\bin\resvg.exe` (downloaded manually
  from github.com/linebender/resvg release v0.47.0 — later releases dropped
  the Windows binary). Already on PATH.
- **LibreOffice** installed to `C:\Program Files\LibreOffice`. winget install
  originally stalled on a slow mirror; the MSI was downloaded directly from
  `mirror.kumi.systems/tdf/…` (~5 MB/s) and installed via elevated msiexec.
- **Noto Sans TTFs** are bundled at `backend/app/assets/fonts/` — do not
  delete. They cover Latin extended + Greek + Cyrillic. CJK/emoji still
  require an additional font (documented limitation in README).

## New in this session — PDF page operations

- **Backend**
  - `backend/app/core/errors.py` — new `InvalidOptionsError` (HTTP 400,
    code `INVALID_OPTIONS`). Reserve `UnsupportedFormatError` for
    wrong-format uploads and `ConversionError` for server-side failures;
    bad page selections raise `InvalidOptionsError`.
  - `backend/app/converters/pdf.py` — `split_pdf` (every_page / every_n /
    ranges), `delete_pdf_pages`, `extract_pdf_pages`, `reorder_pdf_pages`,
    `zip_outputs`, plus validators. Split filenames use dynamic zero-padding
    (`part-01.pdf` up to `part-999.pdf`), min width 2. `_open_pdf` guards
    `doc.is_pdf` so PyMuPDF's general document loader can't slip a
    non-PDF (e.g. `.md`) into a raw `RuntimeError`.
  - Routes at `/api/pdf/{split,delete-pages,extract-pages,reorder-pages}`
    follow the existing `BackgroundTasks` + `tempfile.mkdtemp` +
    `remove_dir` pattern from `/api/convert`. All-page numbers are
    1-indexed in the API surface.
- **Frontend**
  - Router added: `react-router-dom` v6, `<BrowserRouter>` in `main.tsx`.
    Home stays at `/`; tool pages at `/split-pdf`, `/delete-pdf-pages`,
    `/extract-pdf-pages`, `/reorder-pdf-pages` (one canonical slug per
    tool; SEO aliases were considered but deferred).
  - `pdfjs-dist` v4 renders per-page thumbnails; worker URL wired via
    `new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url)` in
    `src/lib/pdfjs.ts`.
  - Drag reorder uses `@dnd-kit/core` + `@dnd-kit/sortable`. The old
    `MergeList` (arrow-buttons only) is unchanged — used only from the
    home page's merge flow.
  - Shared shell `components/PdfToolLayout.tsx` owns the DropZone,
    pdf.js load state, capability gating, and the download flow. Each
    tool page owns only its tool-specific controls.

## Key design decisions (locked in)

- Split returns a single **ZIP archive** — no persistent temp storage
  needed; matches existing `FileResponse` pattern.
- Reorder requires an **exact permutation** of `1..page_count`; missing,
  extra, or duplicate indices → `InvalidOptionsError`.
- Extract disallows duplicates in V1.
- Delete rejects "delete every page" before it would produce an empty PDF.

## Known small things not worth fixing yet

- Starlette's `TestClient` emits a `StarletteDeprecationWarning` about
  `httpx` vs `httpx2`. Cosmetic only.
- The frontend `HomePage` `useEffect` intentionally has `targets`/`missingDep`
  omitted from its dependency list (`eslint-disable-next-line` on that
  line) to avoid loops when resetting on new file selection.
- Pandoc → Typst emits a Typst deprecation notice about `document.set(font: …)`
  when Typst is called; it's harmless and comes from Pandoc's default template.
- One live EPUB → PDF request out of the first ~30 returned a `pandoc rc=43`
  transient "Error producing PDF" from Typst's default template (looked like
  a `conf(…)` init hiccup — possibly Typst's font/package cache warming).
  Every subsequent attempt (and 3× consecutive retries on the same fixture)
  succeeded and produced byte-identical output. Pytest never reproduces it.
  If it recurs in production, look at Typst cache init and consider a warmup
  invocation at startup, or a single automatic retry inside `_run_pandoc`.
- Vite reports the built JS bundle at ~600 KB (from pdf.js). Code-splitting
  the pdf.js worker into its own dynamic import would help, but the
  worker is already a separate chunk (`assets/pdf.worker-*.mjs`, ~2.2 MB).
  The main bundle is fine for now.
- PyMuPDF-generated fixtures embed a modification timestamp, so
  `backend/tests/fixtures/*.pdf` and the EPUB/DOCX fixtures show as
  "modified" in git every time `generate_all()` runs (which happens via
  the `conftest.py` autouse fixture on every pytest session). Commit them
  as-is when unrelated changes are being made — do not fight it.

## How to run right now

```bash
# terminal 1 — backend (uses env PATH additions for pandoc)
cd C:\Users\Aditya\Documents\aio-converter\backend
export PATH="/c/Users/Aditya/AppData/Local/Pandoc:$PATH"
uv run uvicorn app.main:app --port 8000

# terminal 2 — frontend
cd C:\Users\Aditya\Documents\aio-converter\frontend
npm run dev
# open http://localhost:5173
#  - /             → conversions + merge (unchanged)
#  - /split-pdf    → Split PDF (zip output)
#  - /delete-pdf-pages → click thumbs to remove
#  - /extract-pdf-pages → click thumbs to keep (order preserved)
#  - /reorder-pdf-pages → drag thumbs to reorder
```

Tests: `cd backend && uv run pytest` — 69 pass with the same PATH.
Frontend build: `cd frontend && npm run build` — clean.

## Real-PDF smoke coverage

Verified end-to-end against
`C:\Users\Aditya\Downloads\linkedin-profile.pdf` (4 pages, image-only):

- Split every_page → 4-entry zip, one page each.
- Split every_n (n=2) → 2-entry zip, 2 pages each.
- Split ranges [[1,2],[3,4]] → 2-entry zip, 2 pages each.
- Delete [2,4] → 2-page output; pixmap hashes confirm source pages 1 and 3
  survived.
- Extract [3,1] → 2-page output in that order (pixmap-hash verified).
- Reorder [4,3,2,1] → 4-page output reversed (pixmap-hash verified).
- All error cases (delete-all, extract dupes, reorder non-permutation)
  return HTTP 400 with `INVALID_OPTIONS`.

## What's next if we continue

- **Compress PDF** — the plan's biggest remaining keyword opportunity
  (~110K/mo US, ~1.6M/mo IN for "compress pdf"). Trivial version is
  `doc.save(garbage=4, deflate=True, clean=True)`, but users expect
  ~10× reductions on image-heavy PDFs, which needs image detection +
  downsampling + JPEG re-encoding + object cleanup. Not a same-day task.
- SEO alias slugs — plan considered `/remove-pages-from-pdf` as an alias
  for `/delete-pdf-pages` (different search-intent phrasing). Decided
  against for V1; revisit if organic delete-pages traffic stalls.
- OCR fallback for scanned PDFs (still deferred from prior session).
- More format pairs (PDF→PNG, DOCX→TXT, etc.) — add to `CONVERSIONS`
  dict in `backend/app/converters/__init__.py`, add a converter function.
- Font bundling for CJK/emoji in TXT→PDF.
