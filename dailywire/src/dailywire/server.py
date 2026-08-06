"""FastAPI server: serve ./public and ./episodes so a phone on the LAN can subscribe."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .config import Config
from .publish import collect_episodes, format_duration, write_feed, write_index
from .store import Store

log = logging.getLogger(__name__)


def create_app(cfg: Config) -> FastAPI:
    public = cfg.public_path
    episodes = cfg.episodes_path
    public.mkdir(parents=True, exist_ok=True)
    episodes.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title=cfg.podcast.title, docs_url=None, redoc_url=None)

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        return "ok"

    @app.get("/api/episodes")
    def api_episodes() -> JSONResponse:
        with Store(cfg.db_file) as store:
            entries = collect_episodes(cfg, store)
        return JSONResponse(
            [
                {
                    "date": e["date"],
                    "title": e["title"],
                    "duration": format_duration(e["duration_ms"]),
                    "bytes": e["size"],
                    "audio": f"/episodes/{e['path'].name}",
                    "notes": f"/episodes/{e['notes'].name}" if e["notes"] else None,
                }
                for e in entries
            ]
        )

    @app.post("/api/refresh")
    def api_refresh() -> JSONResponse:
        """Rebuild feed.xml and index.html from what's on disk."""
        with Store(cfg.db_file) as store:
            feed = write_feed(cfg, store)
            write_index(cfg, store)
        return JSONResponse({"status": "ok", "feed": str(feed)})

    # Audio first, then the public directory at the root, so /feed.xml and
    # /index.html come from ./public while /episodes/*.mp3 is served in place
    # (no copying a 10 MB file just to publish it).
    app.mount("/episodes", StaticFiles(directory=episodes), name="episodes")
    app.mount("/", StaticFiles(directory=public, html=True), name="public")
    return app


def serve(cfg: Config, host: str | None = None, port: int | None = None) -> None:
    import uvicorn

    # Make sure there is something to serve even on a first run.
    with Store(cfg.db_file) as store:
        write_feed(cfg, store)
        write_index(cfg, store)

    host = host or cfg.server.host
    port = port or cfg.server.port
    log.info("serving %s on http://%s:%d (feed at /feed.xml)", cfg.public_path, host, port)
    uvicorn.run(create_app(cfg), host=host, port=port, log_level="info")
