import sys
import pytest
import chainlit as cl
from pathlib import Path

# Make app.py / config.py importable from the tests/ folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeMessage:
    """
    Stand-in for cl.Message. Chainlit's real Message needs an active
    websocket session/context to send/stream/update, which isn't available
    in a plain pytest run. This fake just records what happened so tests can
    assert on it, without touching any real Chainlit context.
    """

    instances: list["FakeMessage"] = []

    def __init__(self, content: str = "", **kwargs):
        self.content = content
        self.tokens: list[str] = []
        FakeMessage.instances.append(self)

    async def send(self):
        return self

    async def stream_token(self, token: str):
        self.tokens.append(token)
        self.content += token

    async def update(self):
        return self


@pytest.fixture
def fake_message(monkeypatch):
    """Patches cl.Message app-wide for the duration of a test."""
    FakeMessage.instances = []
    monkeypatch.setattr(cl, "Message", FakeMessage)
    return FakeMessage


@pytest.fixture
def fake_user_session(monkeypatch):
    """
    Backs cl.user_session.get/set with a plain dict scoped to one test,
    instead of Chainlit's real per-websocket-session store.
    """
    store: dict = {}

    def _get(key, default=None):
        return store.get(key, default)

    def _set(key, value):
        store[key] = value

    monkeypatch.setattr(cl.user_session, "get", _get)
    monkeypatch.setattr(cl.user_session, "set", _set)
    return store


class _FakeDelta:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.delta = _FakeDelta(content)


class FakeChunk:
    def __init__(self, content=None, choices_empty=False):
        # Mirrors real OpenAI streaming chunks, including the trailing chunk with an empty choices list
        self.choices = [] if choices_empty else [_FakeChoice(content)]


class FakeStream:
    """
    Wraps an async generator to also expose an async close(), mirroring the
    real openai.AsyncStream interface
    """

    def __init__(self, agen):
        self._agen = agen

    def __aiter__(self):
        return self._agen.__aiter__()

    async def close(self):
        await self._agen.aclose()


def make_fake_stream(tokens, raise_after: int | None = None, trailing_usage_chunk=True):
    """
    Build a fake streaming response.

    tokens: list of string tokens to yield, one per chunk
    raise_after: if set, raise mid-stream after this many tokens (simulates
        a dropped connection)
    trailing_usage_chunk: append a chunk with empty `choices`, matching real
        OpenAI's trailing usage-accounting chunk
    """

    async def _agen():
        for i, tok in enumerate(tokens):
            if raise_after is not None and i == raise_after:
                raise RuntimeError("simulated connection drop")
            yield FakeChunk(content=tok)
        if trailing_usage_chunk:
            yield FakeChunk(choices_empty=True)

    return FakeStream(_agen())
