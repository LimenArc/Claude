"""Configuration loading.

Everything is a dataclass with a working default, so a missing or partial
config.toml still produces a runnable pipeline. Secrets are never read from the
file -- only the *name* of the environment variable that holds them.
"""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Source:
    name: str
    url: str
    category: str = "tech"
    weight: float = 1.0


@dataclass
class HackerNewsConfig:
    enabled: bool = True
    min_points: int = 100
    max_items: int = 20


@dataclass
class ArxivConfig:
    enabled: bool = True
    categories: list[str] = field(default_factory=lambda: ["cs.AI", "cs.LG"])
    max_items: int = 20


@dataclass
class IngestConfig:
    user_agent: str = (
        "dailywire/0.1 (+https://github.com/LimenArc/claude; personal podcast generator)"
    )
    per_domain_delay: float = 1.5
    max_concurrency: int = 8
    request_timeout: float = 20.0
    lookback_hours: int = 24
    respect_robots_txt: bool = True
    fetch_full_text: bool = True
    snippet_threshold: int = 600
    max_full_text_fetches: int = 40
    hackernews: HackerNewsConfig = field(default_factory=HackerNewsConfig)
    arxiv: ArxivConfig = field(default_factory=ArxivConfig)


@dataclass
class ClusterConfig:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cosine_threshold: float = 0.62
    tfidf_threshold: float = 0.35
    max_cluster_span_hours: float = 36.0


@dataclass
class Quota:
    min: int = 0
    max: int = 99


@dataclass
class RankingConfig:
    max_stories: int = 12
    target_runtime_minutes: float = 12.0
    words_per_minute: int = 155
    recency_half_life: float = 10.0
    weight_recency: float = 1.0
    weight_source: float = 0.8
    weight_corroboration: float = 1.0
    weight_hn: float = 0.5
    quotas: dict[str, Quota] = field(
        default_factory=lambda: {
            "world": Quota(3, 5),
            "ai": Quota(2, 5),
            "tech": Quota(2, 4),
            "science": Quota(0, 2),
        }
    )


@dataclass
class LLMConfig:
    provider: str = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    api_key_env: str = "DAILYWIRE_LLM_API_KEY"
    temperature: float = 0.4
    max_tokens: int = 1200
    timeout: float = 90.0
    max_retries: int = 3


@dataclass
class ScriptConfig:
    spell_out_numbers: bool = True
    strip_urls: bool = True
    show_name: str = "Dailywire"
    sign_off: str = "That's your briefing. Sources are linked in the show notes."


@dataclass
class PiperConfig:
    binary: str = "piper"
    voice: str = "./voices/en_US-lessac-medium.onnx"
    speaker: int = 0
    length_scale: float = 1.0


@dataclass
class KokoroConfig:
    voice: str = "af_heart"
    speed: float = 1.0
    lang_code: str = "a"


@dataclass
class HostedTTSConfig:
    base_url: str = "https://api.openai.com/v1"
    model: str = "tts-1"
    voice: str = "alloy"
    api_key_env: str = "DAILYWIRE_TTS_API_KEY"
    response_format: str = "mp3"


@dataclass
class TTSConfig:
    provider: str = "piper"
    chunk_chars: int = 1800
    loudness_i: float = -16.0
    loudness_tp: float = -1.5
    loudness_lra: float = 11.0
    bitrate: str = "96k"
    sample_rate: int = 22050
    piper: PiperConfig = field(default_factory=PiperConfig)
    kokoro: KokoroConfig = field(default_factory=KokoroConfig)
    hosted: HostedTTSConfig = field(default_factory=HostedTTSConfig)


@dataclass
class PodcastConfig:
    title: str = "Dailywire"
    subtitle: str = "Your automated morning briefing"
    description: str = "A machine-assembled daily briefing."
    author: str = "dailywire"
    email: str = "noreply@localhost"
    language: str = "en-us"
    base_url: str = "http://127.0.0.1:8000"
    explicit: bool = False
    category: str = "News"
    subcategory: str = "Tech News"
    artwork: str = ""


@dataclass
class GeneralConfig:
    episodes_dir: str = "./episodes"
    public_dir: str = "./public"
    db_path: str = "./dailywire.db"
    timezone: str = "America/New_York"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    podcast: PodcastConfig = field(default_factory=PodcastConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)
    sources: list[Source] = field(default_factory=list)
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    script: ScriptConfig = field(default_factory=ScriptConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    # Directory the config file lives in; relative paths resolve against it.
    root: Path = field(default_factory=Path.cwd)

    def path(self, value: str) -> Path:
        p = Path(value).expanduser()
        return p if p.is_absolute() else (self.root / p).resolve()

    @property
    def episodes_path(self) -> Path:
        return self.path(self.general.episodes_dir)

    @property
    def public_path(self) -> Path:
        return self.path(self.general.public_dir)

    @property
    def db_file(self) -> Path:
        return self.path(self.general.db_path)


def _coerce(cls: type, value: Any) -> Any:
    """Build a flat dataclass instance from a plain dict.

    Unknown keys are ignored rather than fatal: a config written for a newer
    version of dailywire should still start. Nested sections are popped and
    coerced by the caller, so this only ever sees scalars and lists.
    """
    if not isinstance(value, dict):
        return cls()
    names = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in value.items() if k in names})


def _quotas(raw: Any) -> dict[str, Quota]:
    out: dict[str, Quota] = {}
    if isinstance(raw, dict):
        for category, spec in raw.items():
            if isinstance(spec, dict):
                out[category] = Quota(int(spec.get("min", 0)), int(spec.get("max", 99)))
            elif isinstance(spec, int):  # bare integer means "at most this many"
                out[category] = Quota(0, spec)
    return out


def load_config(path: str | Path | None = None) -> Config:
    """Load config.toml, falling back to defaults for anything absent."""
    cfg = Config()
    if path is None:
        for candidate in (Path.cwd() / "config.toml", Path(__file__).parent.parent.parent / "config.toml"):
            if candidate.exists():
                path = candidate
                break
    if path is None:
        cfg.root = Path.cwd()
        return cfg

    path = Path(path)
    with path.open("rb") as fh:
        data = tomllib.load(fh)

    cfg.root = path.parent.resolve()
    if "general" in data:
        cfg.general = _coerce(GeneralConfig, data["general"])
    if "podcast" in data:
        cfg.podcast = _coerce(PodcastConfig, data["podcast"])
    if "ingest" in data:
        ingest = dict(data["ingest"])
        hn = ingest.pop("hackernews", {})
        arxiv = ingest.pop("arxiv", {})
        cfg.ingest = _coerce(IngestConfig, ingest)
        cfg.ingest.hackernews = _coerce(HackerNewsConfig, hn)
        cfg.ingest.arxiv = _coerce(ArxivConfig, arxiv)
    if "cluster" in data:
        cfg.cluster = _coerce(ClusterConfig, data["cluster"])
    if "ranking" in data:
        ranking = dict(data["ranking"])
        quotas = ranking.pop("quotas", None)
        cfg.ranking = _coerce(RankingConfig, ranking)
        if quotas is not None:
            cfg.ranking.quotas = _quotas(quotas)
    if "llm" in data:
        cfg.llm = _coerce(LLMConfig, data["llm"])
    if "script" in data:
        cfg.script = _coerce(ScriptConfig, data["script"])
    if "tts" in data:
        tts = dict(data["tts"])
        piper = tts.pop("piper", {})
        kokoro = tts.pop("kokoro", {})
        hosted = tts.pop("hosted", {})
        cfg.tts = _coerce(TTSConfig, tts)
        cfg.tts.piper = _coerce(PiperConfig, piper)
        cfg.tts.kokoro = _coerce(KokoroConfig, kokoro)
        cfg.tts.hosted = _coerce(HostedTTSConfig, hosted)
    if "server" in data:
        cfg.server = _coerce(ServerConfig, data["server"])
    cfg.sources = [_coerce(Source, s) for s in data.get("sources", [])]
    return cfg
