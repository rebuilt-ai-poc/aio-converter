"""FastAPI app entry."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import register_error_handlers, router
from .core.config import FRONTEND_DIST


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="All-in-One Local File Converter",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Dev-only CORS. The frontend is served from the same origin in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(router)


def _mount_frontend(app_: FastAPI) -> None:
    dist = FRONTEND_DIST
    if not dist.is_dir():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app_.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    index = dist / "index.html"

    @app_.get("/{full_path:path}")
    async def spa(full_path: str):
        # SPA fallback: any GET not matched by /api/* or /assets/* returns index.html.
        candidate = dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


_mount_frontend(app)
