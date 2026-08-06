# dailywire

A self-hosted daily news podcast generator. It runs unattended every morning,
reads the web, and leaves an MP3 briefing plus a valid podcast feed on your own
machine. Subscribe from your phone over the LAN; nothing leaves your network
except the requests to the sources and (optionally) your language model.

```
feeds + Hacker News + arXiv
        │
        ▼
  ingest ──► dedupe ──► cluster ──► rank ──► script ──► narrate ──► publish
   RSS       SQLite     embeddings  quotas    LLM        Piper      MP3 + RSS
   HN API    simhash    or TF-IDF   runtime   2 stages   /Kokoro    chapters
   arXiv                                                 /hosted    feed.xml
```

## Quick start

```bash
cd dailywire
uv venv && uv pip install -e .

# What's missing on this machine?
uv run dailywire doctor

# Build today's episode
uv run dailywire run

# Serve it to your phone
uv run dailywire serve            # http://<your-lan-ip>:8000/feed.xml
```

You need **ffmpeg** on PATH, and a TTS voice (see below). Everything else has a
working fallback.

### The three external pieces

| Piece | Default | Needed for | Fallback if absent |
| --- | --- | --- | --- |
| ffmpeg | system package | concatenating and normalising audio | none — required |
| TTS | Piper, local | narration | `--skip-audio` writes the script only |
| LLM | OpenAI-compatible endpoint | summaries and the script | headline-only briefing |
| Embeddings | `sentence-transformers` | clustering | TF-IDF |
| trafilatura / readability | installed by default | full article text | feed snippets |

**Piper** (default voice, fully offline):

```bash
# binary: https://github.com/rhasspy/piper/releases
mkdir -p voices && cd voices
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

**LLM** — any OpenAI-compatible `/chat/completions` endpoint. Point
`[llm].base_url` and `[llm].model` at it and put the key in the environment
variable named by `[llm].api_key_env`:

```bash
cp .env.example .env      # then edit
```

A local llama.cpp or Ollama server works: `base_url = "http://localhost:11434/v1"`.
Set `provider = "anthropic"` to use the Messages API instead.

## What it does

**Ingest.** Every feed in `[[sources]]`, plus Hacker News front-page stories
over 100 points from the last 24 hours (Algolia API), plus new arXiv cs.AI and
cs.LG submissions. When a feed only carries a snippet, the article is fetched
and the body extracted with trafilatura (readability-lxml as backup). Requests
carry a real User-Agent, honour robots.txt, and are rate-limited per domain
(1.5s by default, 3s for arXiv as they ask). The two JSON/Atom API endpoints are
called without a robots check — they are documented programmatic APIs, not
crawlable pages; every article page fetch does check.

**Dedupe.** Every item ever seen is stored in SQLite by URL hash and title
simhash. Anything seen before is dropped, so a story cannot repeat across days
even if it resurfaces in a different feed. Note the trade-off: items ingested
but *not* selected are still marked seen, so they don't come back tomorrow.

**Cluster.** Items are embedded with a local sentence-transformers model and
merged by single-link agglomeration above `cosine_threshold`. Without the model
installed, TF-IDF vectors are used with a looser threshold. Clusters never span
more than `max_cluster_span_hours`.

**Rank.** Each cluster scores on recency (exponential decay, configurable
half-life), source weight, cross-source corroboration, and Hacker News points.
The top N (default 12) are selected subject to the target runtime, with
per-category minimums and maximums — the minimums are honoured first, which is
what stops a busy AI news day from crowding world news out of the episode.

**Script.** One LLM call per cluster produces a two-to-four sentence factual
summary; a final call stitches them into a spoken script with a cold open,
category segments with verbal transitions, and a sign-off. The prompts forbid
bullets, URLs, bare numerals, unexpanded acronyms, and any reproduction of
source prose beyond a short quoted phrase; claims are attributed to the outlet
that reported them. Because models drift on those rules, a deterministic pass
afterwards strips markup and URLs and spells numbers out (`4.2%` → "four point
two percent", `1998` → "nineteen ninety-eight"), then lints what's left.

**Narrate.** Text is chunked on sentence boundaries, synthesized chunk by
chunk, concatenated with ffmpeg, and loudness-normalised to −16 LUFS with
two-pass `loudnorm`. Providers: `piper` (default, local), `kokoro` (local), and
`hosted` (any OpenAI-compatible `/audio/speech` endpoint, keyed off an env var).

**Publish.** `./episodes/YYYY-MM-DD.mp3` with ID3v2 tags and a CHAP/CTOC
chapter per segment, the script beside it as `.md`, a regenerated RSS 2.0 feed
with the iTunes namespace at `./public/feed.xml`, and a small index page.
`dailywire serve` puts `./public` at `/` and `./episodes` at `/episodes`.

## Commands

```
dailywire run [--date YYYY-MM-DD] [--dry-run] [--skip-audio] [--tts piper|kokoro|hosted] [--force]
dailywire serve [--host H] [--port P]
dailywire feed          # regenerate feed.xml and index.html from what's on disk
dailywire list          # published episodes
dailywire doctor        # check ffmpeg, TTS, LLM, embeddings, extractors
dailywire prune --days 365
```

`--dry-run` prints the script and writes nothing to the database, which is the
fastest way to iterate on prompts and source weights.

## Running it every morning

`base_url` in `[podcast]` must be the address your phone can reach — the
machine's LAN IP, not `127.0.0.1`, or podcast apps will fail to download.

systemd, generating at 6am and leaving the server up:

```ini
# ~/.config/systemd/user/dailywire.service
[Unit]
Description=dailywire episode build
[Service]
Type=oneshot
WorkingDirectory=%h/dailywire
ExecStart=%h/.local/bin/uv run dailywire run

# ~/.config/systemd/user/dailywire.timer
[Unit]
Description=Build the dailywire episode every morning
[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now dailywire.timer
```

Or cron: `0 6 * * * cd ~/dailywire && uv run dailywire run >> run.log 2>&1`.

## Configuration

Everything lives in `config.toml`, which ships with a working source list:
AI research and industry (Google Research, OpenAI, Anthropic, DeepMind, MIT
Tech Review, Import AI, The Batch), general tech (Ars Technica, The Verge,
TechCrunch, Hacker News), world news from outlets with deliberately different
national and editorial vantage points (BBC, Al Jazeera, Deutsche Welle,
France 24, NPR), and science (Nature, Quanta). Corroboration scoring rewards a
story carried across several of them, so keeping that spread wide is doing real
work — narrow it and the ranking gets less informative, not just less varied.

Secrets are never read from the config file; it only names the environment
variables to read them from.

## Tests

```bash
uv run pytest
```

The suite covers hashing and dedupe, clustering (TF-IDF path), ranking quotas
and runtime budgeting, the speakability rules, segment parsing, feed validity
(re-parsed with feedparser), and the config loader. Nothing in it touches the
network, ffmpeg, or a model.

## Licence

MIT.
