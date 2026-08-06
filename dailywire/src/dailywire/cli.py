"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import date as date_cls
from pathlib import Path

from .config import Config, load_config

log = logging.getLogger("dailywire")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("httpx", "httpcore", "urllib3", "sentence_transformers", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _parse_date(value: str) -> date_cls:
    try:
        return date_cls.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dailywire", description="Self-hosted daily news podcast generator."
    )
    parser.add_argument("-c", "--config", type=Path, default=None, help="path to config.toml")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="build today's episode end to end")
    run.add_argument("--date", type=_parse_date, help="episode date (default: today)")
    run.add_argument("--dry-run", action="store_true", help="script only; no audio, no database writes")
    run.add_argument("--skip-audio", action="store_true", help="script and show notes only")
    run.add_argument("--tts", dest="tts_provider", help="override the TTS provider for this run")
    run.add_argument("--force", action="store_true", help="regenerate an episode that already exists")

    serve = sub.add_parser("serve", help="serve ./public and ./episodes over HTTP")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)

    sub.add_parser("feed", help="regenerate feed.xml and index.html from what's on disk")
    sub.add_parser("list", help="list published episodes")
    sub.add_parser("doctor", help="check that the pieces this needs are installed")

    prune = sub.add_parser("prune", help="forget old items that never made an episode")
    prune.add_argument("--days", type=int, default=365)

    return parser


def cmd_run(cfg: Config, args: argparse.Namespace) -> int:
    from .pipeline import RunOptions, run

    episode = run(
        cfg,
        RunOptions(
            date=args.date,
            dry_run=args.dry_run,
            skip_audio=args.skip_audio,
            tts_provider=args.tts_provider,
            force=args.force,
        ),
    )
    if episode is None:
        return 1
    if args.dry_run:
        print("\n" + episode.script + "\n")
    return 0


def cmd_serve(cfg: Config, args: argparse.Namespace) -> int:
    from .server import serve

    serve(cfg, args.host, args.port)
    return 0


def cmd_feed(cfg: Config, _args: argparse.Namespace) -> int:
    from .publish import write_feed, write_index
    from .store import Store

    with Store(cfg.db_file) as store:
        feed = write_feed(cfg, store)
        write_index(cfg, store)
    print(feed)
    return 0


def cmd_list(cfg: Config, _args: argparse.Namespace) -> int:
    from .publish import collect_episodes, format_duration
    from .store import Store

    with Store(cfg.db_file) as store:
        entries = collect_episodes(cfg, store)
    if not entries:
        print("no episodes yet")
        return 0
    for entry in entries:
        duration = format_duration(entry["duration_ms"]) if entry["duration_ms"] else "?"
        print(f"{entry['date']}  {duration:>8}  {entry['size'] / 1e6:5.1f} MB  {entry['path'].name}")
    return 0


def cmd_prune(cfg: Config, args: argparse.Namespace) -> int:
    from .store import Store

    with Store(cfg.db_file) as store:
        removed = store.prune(args.days)
    print(f"forgot {removed} items older than {args.days} days")
    return 0


def cmd_doctor(cfg: Config, _args: argparse.Namespace) -> int:
    """Report on every external dependency, then exit non-zero if audio can't work."""
    ok = True

    def check(label: str, good: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if good else 'FAIL'}  {label}{f'  ({detail})' if detail else ''}")

    print(f"config: {cfg.root}")
    print("\nAudio:")
    ffmpeg = shutil.which("ffmpeg")
    check("ffmpeg", bool(ffmpeg), ffmpeg or "not on PATH -- required to render episodes")
    ok = ok and bool(ffmpeg)
    ffprobe = shutil.which("ffprobe")
    check("ffprobe", bool(ffprobe), ffprobe or "not on PATH -- chapter timings will be wrong")

    print("\nText to speech:")
    from .tts import get_provider as get_tts
    from .tts.base import TTSError

    try:
        provider = get_tts(cfg)
        check(f"provider {cfg.tts.provider}", True, provider.describe())
    except TTSError as exc:
        check(f"provider {cfg.tts.provider}", False, str(exc).split(" -- ")[0])
        ok = False

    print("\nLanguage model:")
    from .llm import get_provider as get_llm

    llm = get_llm(cfg.llm)
    if llm is None:
        check("LLM", False, f"not configured; set {cfg.llm.api_key_env} for real summaries")
    else:
        check("LLM", True, llm.describe())

    print("\nClustering:")
    from .cluster import load_embedder

    model = load_embedder(cfg.cluster.embedding_model)
    check(
        "embeddings",
        model is not None,
        cfg.cluster.embedding_model if model else "unavailable; TF-IDF fallback will be used",
    )

    print("\nExtraction:")
    for module in ("trafilatura", "readability"):
        try:
            __import__(module)
            check(module, True)
        except ImportError:
            check(module, False, "not installed; feed snippets only")

    print("\nSources:")
    check(f"{len(cfg.sources)} feeds configured", bool(cfg.sources))
    print()
    return 0 if ok else 1


COMMANDS = {
    "run": cmd_run,
    "serve": cmd_serve,
    "feed": cmd_feed,
    "list": cmd_list,
    "prune": cmd_prune,
    "doctor": cmd_doctor,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    cfg = load_config(args.config)
    try:
        return COMMANDS[args.command](cfg, args)
    except KeyboardInterrupt:
        log.warning("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
