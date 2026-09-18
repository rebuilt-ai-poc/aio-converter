@echo off
REM ============================================================
REM  aio-converter — one-shot launcher
REM  Starts the FastAPI backend and Vite frontend, then opens
REM  the browser so you can drop in any supported document and
REM  pick a conversion.
REM ============================================================

setlocal

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

REM --- Ensure Pandoc is discoverable (winget installs per-user, off PATH) ---
if exist "%LOCALAPPDATA%\Pandoc\pandoc.exe" (
    set "PATH=%LOCALAPPDATA%\Pandoc;%PATH%"
)

REM --- Sanity checks --------------------------------------------------------
where uv >nul 2>&1
if errorlevel 1 (
    echo [run.bat] ERROR: 'uv' not found on PATH.
    echo           Install from https://docs.astral.sh/uv/ and re-run.
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [run.bat] ERROR: 'npm' not found on PATH.
    echo           Install Node.js from https://nodejs.org/ and re-run.
    exit /b 1
)

REM --- Backend venv (first run only) ---------------------------------------
if not exist "%ROOT%\backend\.venv" (
    echo [run.bat] Creating backend virtualenv and installing requirements (one-time^)...
    pushd "%ROOT%\backend" || exit /b 1
    call uv sync
    if errorlevel 1 (
        popd
        echo [run.bat] ERROR: uv sync failed.
        exit /b 1
    )
    popd
)

REM --- Frontend deps (first run only) --------------------------------------
if not exist "%ROOT%\frontend\node_modules" (
    echo [run.bat] Installing frontend dependencies (one-time^)...
    pushd "%ROOT%\frontend" || exit /b 1
    call npm install
    if errorlevel 1 (
        popd
        echo [run.bat] ERROR: npm install failed.
        exit /b 1
    )
    popd
)

REM --- Launch backend -------------------------------------------------------
echo [run.bat] Starting backend on http://localhost:8000 ...
start "aio-converter backend" cmd /k "cd /d "%ROOT%\backend" && set "PATH=%LOCALAPPDATA%\Pandoc;%PATH%" && uv run uvicorn app.main:app --port 8000"

REM --- Launch frontend ------------------------------------------------------
echo [run.bat] Starting frontend on http://localhost:5173 ...
start "aio-converter frontend" cmd /k "cd /d "%ROOT%\frontend" && npm run dev"

REM --- Give Vite a moment, then open the browser ---------------------------
REM  Small wait so the browser doesn't race the dev server's boot.
powershell -NoProfile -Command "Start-Sleep -Seconds 4" >nul 2>&1
start "" http://localhost:5173

echo.
echo [run.bat] Two terminal windows are now running:
echo           * backend  — FastAPI  (http://localhost:8000)
echo           * frontend — Vite dev (http://localhost:5173)
echo           Close either window to stop that service.
echo.

endlocal
