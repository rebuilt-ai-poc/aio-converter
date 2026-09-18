# Installation

## 1. Python backend

Requires **Python 3.12+**. The backend uses [`uv`](https://github.com/astral-sh/uv) for env/dep management.

```bash
cd backend
uv sync
```

This creates a `.venv/` with all pinned dependencies from `pyproject.toml`.

## 2. Native tools

The nine conversions map to these engines:

| Engine       | Needed for                     |
| ------------ | ------------------------------ |
| PyMuPDF      | all PDF-source ops             |
| ReportLab    | TXT → PDF                      |
| Pillow       | PNG → JPEG, SVG → JPEG         |
| Pandoc       | Markdown → PDF                 |
| Typst        | Markdown → PDF (pandoc engine) |
| LibreOffice  | DOCX → PDF                     |
| resvg        | SVG → JPEG                     |

Python engines install automatically with `uv sync`. The four native ones:

### Windows

```powershell
winget install --id JohnMacFarlane.Pandoc
winget install --id Typst.Typst
winget install --id TheDocumentFoundation.LibreOffice
# resvg has no winget package — download resvg-win64.zip from
# https://github.com/linebender/resvg/releases and place resvg.exe on PATH
```

If a winget package fails to extract, download the release zip directly from GitHub.

### macOS

```bash
brew install pandoc typst
brew install --cask libreoffice
# resvg: download resvg-macos-*.zip from https://github.com/linebender/resvg/releases
```

### Linux

```bash
sudo apt-get install pandoc libreoffice
cargo install typst-cli   # or grab the release tarball
# resvg: download resvg-linux-x86_64.tar.gz from https://github.com/linebender/resvg/releases
```

## 3. Frontend

Requires **Node 20+**.

```bash
cd frontend
npm install
npm run dev            # dev server on :5173
# or, for a single-app local deployment:
npm run build          # writes frontend/dist/
```

## 4. Verify

```bash
python scripts/check_dependencies.py
```

Should list every engine as ✓ with 9 / 9 conversions available.

## 5. Run

Two-process (dev):

```bash
# terminal 1
cd backend && uv run uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend && npm run dev
```

Single-process (production/local):

```bash
cd frontend && npm run build
cd ../backend && uv run uvicorn app.main:app --port 8000
# open http://localhost:8000
```
