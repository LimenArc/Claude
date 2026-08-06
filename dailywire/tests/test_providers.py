"""LLM and TTS provider tests, all over httpx MockTransport."""

from __future__ import annotations

import httpx
import pytest

from dailywire.config import Config, HostedTTSConfig, LLMConfig, TTSConfig
from dailywire.llm import get_provider as get_llm
from dailywire.llm.anthropic import AnthropicLLM
from dailywire.llm.base import LLMError
from dailywire.llm.openai_compat import OpenAICompatibleLLM
from dailywire.tts import get_provider as get_tts
from dailywire.tts.base import TTSError
from dailywire.tts.hosted import HostedTTS
from dailywire.tts.piper import PiperTTS


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# -- OpenAI-compatible LLM ---------------------------------------------------


def openai_reply(text: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def test_openai_compatible_sends_system_and_user_and_returns_text(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "secret-key")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = request.read().decode()
        return httpx.Response(200, json=openai_reply("  A summary.  "))

    cfg = LLMConfig(base_url="https://llm.example/v1", model="m", api_key_env="TEST_LLM_KEY")
    llm = OpenAICompatibleLLM(cfg, client=client(handler))
    assert llm.complete("SYSTEM", "USER") == "A summary."
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["auth"] == "Bearer secret-key"
    assert '"SYSTEM"' in captured["body"] and '"USER"' in captured["body"]
    assert '"model":"m"' in captured["body"]


def test_openai_compatible_works_without_a_key():
    """Local servers (llama.cpp, Ollama) need no Authorization header."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(200, json=openai_reply("ok"))

    cfg = LLMConfig(base_url="http://localhost:11434/v1", model="m", api_key_env="UNSET_VAR_X")
    llm = OpenAICompatibleLLM(cfg, client=client(handler))
    assert llm.available()
    assert llm.complete("s", "u") == "ok"


def test_openai_compatible_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json=openai_reply("finally"))

    cfg = LLMConfig(base_url="https://llm.example/v1", model="m", max_retries=3)
    assert OpenAICompatibleLLM(cfg, client=client(handler)).complete("s", "u") == "finally"
    assert attempts["n"] == 3


def test_openai_compatible_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    cfg = LLMConfig(base_url="https://llm.example/v1", model="m", max_retries=2)
    with pytest.raises(LLMError, match="after 2 attempts"):
        OpenAICompatibleLLM(cfg, client=client(handler)).complete("s", "u")


def test_openai_compatible_does_not_retry_a_bad_request():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="bad model")

    cfg = LLMConfig(base_url="https://llm.example/v1", model="m", max_retries=3)
    with pytest.raises(LLMError, match="HTTP 400"):
        OpenAICompatibleLLM(cfg, client=client(handler)).complete("s", "u")
    assert calls["n"] == 1


def test_openai_compatible_handles_a_malformed_body(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    cfg = LLMConfig(base_url="https://llm.example/v1", model="m", max_retries=2)
    with pytest.raises(LLMError, match="malformed"):
        OpenAICompatibleLLM(cfg, client=client(handler)).complete("s", "u")


# -- Anthropic ---------------------------------------------------------------


def test_anthropic_provider_shape(monkeypatch):
    monkeypatch.setenv("TEST_ANTHROPIC_KEY", "k")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["version"] = request.headers.get("anthropic-version")
        captured["key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Hello."}]})

    cfg = LLMConfig(provider="anthropic", base_url="https://api.anthropic.com/v1",
                    model="claude-sonnet-5", api_key_env="TEST_ANTHROPIC_KEY")
    llm = AnthropicLLM(cfg, client=client(handler))
    assert llm.available()
    assert llm.complete("sys", "user") == "Hello."
    assert captured["url"].endswith("/messages")
    assert captured["key"] == "k" and captured["version"]


def test_anthropic_without_a_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = LLMConfig(provider="anthropic", model="m", api_key_env="UNSET_VAR_Y")
    assert not AnthropicLLM(cfg).available()


# -- provider selection ------------------------------------------------------


def test_get_llm_returns_none_when_unconfigured():
    assert get_llm(LLMConfig(provider="none")) is None


def test_get_llm_rejects_an_unknown_provider():
    with pytest.raises(LLMError, match="unknown LLM provider"):
        get_llm(LLMConfig(provider="wat"))


def test_get_llm_falls_back_to_none_when_the_provider_is_unusable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = LLMConfig(provider="anthropic", model="m", api_key_env="UNSET_VAR_Z")
    assert get_llm(cfg) is None


# -- hosted TTS --------------------------------------------------------------


def test_hosted_tts_posts_and_writes_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_TTS_KEY", "tts-secret")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.read().decode()
        return httpx.Response(200, content=b"ID3-audio-bytes")

    cfg = HostedTTSConfig(base_url="https://tts.example/v1", model="tts-1", voice="alloy",
                          api_key_env="TEST_TTS_KEY")
    provider = HostedTTS(TTSConfig(), cfg, client=client(handler))
    assert provider.available() and provider.suffix == ".mp3"

    out = provider.synthesize("Hello there.", tmp_path / "chunk.mp3")
    assert out.read_bytes() == b"ID3-audio-bytes"
    assert captured["url"] == "https://tts.example/v1/audio/speech"
    assert "Hello there." in captured["body"]


def test_hosted_tts_retries_on_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_TTS_KEY", "k")
    monkeypatch.setattr("time.sleep", lambda *_: None)
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, content=b"audio")

    provider = HostedTTS(TTSConfig(), HostedTTSConfig(api_key_env="TEST_TTS_KEY"),
                         client=client(handler))
    provider.synthesize("text", tmp_path / "c.mp3")
    assert attempts["n"] == 2


def test_hosted_tts_without_a_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("UNSET_TTS_KEY", raising=False)
    provider = HostedTTS(TTSConfig(), HostedTTSConfig(api_key_env="UNSET_TTS_KEY"))
    assert not provider.available()


# -- piper -------------------------------------------------------------------


def test_piper_is_unavailable_without_a_voice(cfg):
    provider = PiperTTS(cfg.tts, cfg.tts.piper, root=cfg.root)
    assert not provider.available()


def test_piper_synthesize_invokes_the_binary(cfg, tmp_path, monkeypatch):
    voice = tmp_path / "voice.onnx"
    voice.write_bytes(b"fake-voice")
    cfg.tts.piper.voice = str(voice)
    cfg.tts.piper.binary = "/usr/bin/piper-fake"
    captured: dict = {}

    class Result:
        returncode = 0
        stderr = b""

    def fake_run(cmd, input=None, capture_output=False, check=False):
        captured["cmd"] = cmd
        captured["input"] = input
        Path = type(tmp_path)
        Path(cmd[cmd.index("--output_file") + 1]).write_bytes(b"RIFF")
        return Result()

    monkeypatch.setattr("dailywire.tts.piper.subprocess.run", fake_run)
    monkeypatch.setattr("dailywire.tts.piper.shutil.which", lambda name: name)

    provider = PiperTTS(cfg.tts, cfg.tts.piper, root=cfg.root)
    assert provider.available()
    out = provider.synthesize("Good morning.", tmp_path / "chunk.wav")

    assert out.read_bytes() == b"RIFF"
    assert captured["input"] == b"Good morning."
    assert "--model" in captured["cmd"] and str(voice) in captured["cmd"]


def test_piper_failure_raises(cfg, tmp_path, monkeypatch):
    voice = tmp_path / "voice.onnx"
    voice.write_bytes(b"v")
    cfg.tts.piper.voice = str(voice)

    class Result:
        returncode = 1
        stderr = b"voice model is corrupt"

    monkeypatch.setattr("dailywire.tts.piper.subprocess.run", lambda *a, **k: Result())
    monkeypatch.setattr("dailywire.tts.piper.shutil.which", lambda name: name)
    provider = PiperTTS(cfg.tts, cfg.tts.piper, root=cfg.root)
    with pytest.raises(TTSError, match="corrupt"):
        provider.synthesize("text", tmp_path / "c.wav")


def test_get_tts_rejects_an_unknown_provider():
    with pytest.raises(TTSError, match="unknown TTS provider"):
        get_tts(Config(), "gramophone")


def test_get_tts_refuses_an_unusable_provider(cfg):
    """Better a loud failure than an episode in an unexpected voice."""
    with pytest.raises(TTSError, match="not usable"):
        get_tts(cfg, "piper")
