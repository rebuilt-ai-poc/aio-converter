# Handoff — 2026-09-17

## Where things stand

All **12 conversions** implemented (9 original + EPUB → {TXT, MD, PDF}),
tested via pytest (37/37 pass, no skips) and verified end-to-end via HTTP
against real fixture files (29/29 structural checks pass across two rounds).
Frontend types clean, `npm run build` succeeds. Dependency checker reports
**12/12**. EPUB support reuses the existing Pandoc integration via a shared
`_run_pandoc` helper — no new dependencies.

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

## Known small things not worth fixing yet

- Starlette's `TestClient` emits a `StarletteDeprecationWarning` about
  `httpx` vs `httpx2`. Cosmetic only.
- The frontend `App.tsx` `useEffect` intentionally has `targets`/`missingDep`
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
```

Tests: `cd backend && uv run pytest` — all 37 pass with the same PATH.

## What's next if we continue

Not on this machine's roadmap, but the architecture is set up for:
- OCR fallback for scanned PDFs (see the "No extractable text detected"
  message returned by `pdf_to_txt`).
- More format pairs (PDF→PNG, DOCX→TXT, etc.) — add to `CONVERSIONS` dict
  in `backend/app/converters/__init__.py`, add a converter function.
- Font bundling for CJK/emoji in TXT→PDF.
