import pytest
import app
from tests.conftest import make_fake_stream
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_multi_turn_context_and_error_handling(
    fake_message, fake_user_session, monkeypatch
):
    # Simulate Chainlit calling @cl.on_chat_start when a session begins
    await app.start()

    request_log = []  # captures the `messages` payload sent on each call
    call_count = {"n": 0}

    def stream_factory(*args, **kwargs):
        request_log.append(kwargs["messages"])
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            return make_fake_stream(["Hello", " there"])
        if n == 1:
            return make_fake_stream(["Second", " reply"])
        return make_fake_stream(["Oops", " more"], raise_after=1)

    monkeypatch.setattr(
        app.client.chat.completions,
        "create",
        AsyncMock(side_effect=stream_factory),
    )

    # --- Turn 1 ---
    await app.main(fake_message(content="Hi"))
    history = fake_user_session["message_history"]
    assert history[-1] == {"role": "assistant", "content": "Hello there"}

    # --- Turn 2: the actual regression this test targets ---
    # Verify the SECOND request's payload includes the FIRST exchange, since
    # this is exactly the "only the first message works" bug class from
    # earlier in this project's history.
    await app.main(fake_message(content="How are you?"))
    second_request_messages = request_log[1]
    assert {"role": "user", "content": "Hi"} in second_request_messages
    assert {"role": "assistant", "content": "Hello there"} in second_request_messages
    assert {"role": "user", "content": "How are you?"} in second_request_messages

    history = fake_user_session["message_history"]
    assert history[-1] == {"role": "assistant", "content": "Second reply"}

    # --- Turn 3: mid-stream failure must degrade gracefully ---
    await app.main(fake_message(content="This will fail"))
    bot_reply = fake_message.instances[-1]  # main() creates this internally

    # The user must see SOME response, not empty content or a raw crash
    assert bot_reply.content  # not empty
    assert app.ERROR_MARKER in bot_reply.content

    # The failed turn must NOT corrupt history with a fabricated assistant
    # reply. The user's own message is legitimately recorded; what must be
    # absent is any assistant entry for the broken response.
    history = fake_user_session["message_history"]
    assert history[-1] == {"role": "user", "content": "This will fail"}
    assert not any(
        m["content"].startswith("Oops") for m in history if m["role"] == "assistant"
    )


@pytest.mark.asyncio
async def test_trailing_empty_choices_chunk_does_not_crash(
    fake_message, fake_user_session, monkeypatch
):
    """
    Some providers (OpenAI included) send a final usage-only chunk with an empty `choices`list.
    This must not raise IndexError.
    """
    await app.start()

    async def create_stream(*args, **kwargs):
        return make_fake_stream(["All", " good"], trailing_usage_chunk=True)

    monkeypatch.setattr(
        app.client.chat.completions,
        "create",
        AsyncMock(side_effect=create_stream),
    )

    await app.main(fake_message(content="Hello"))
    bot_reply = fake_message.instances[-1]

    assert bot_reply.content == "All good"
    history = fake_user_session["message_history"]
    assert history[-1] == {"role": "assistant", "content": "All good"}
