from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from typing import cast
import chainlit as cl
import logging
import config

SYSTEM_PROMPT = {"role": "system", "content": config.SYSTEM_PROMPT}
MAX_HISTORY_MESSAGES = config.MAX_HISTORY_MESSAGES

client = AsyncOpenAI(
    base_url=config.API_ENDPOINT,
    api_key=config.API_KEY,
    timeout=config.REQUEST_TIMEOUT,
    max_retries=config.MAX_RETRIES,
)


@cl.on_chat_start
async def start():
    cl.user_session.set("message_history", [SYSTEM_PROMPT])


@cl.on_message
async def main(message: cl.Message):
    message_history = cl.user_session.get("message_history") or [SYSTEM_PROMPT]
    message_history.append({"role": "user", "content": message.content})

    msg = cl.Message(content="")
    await msg.send()
    full_response = ""

    try:
        stream = await client.chat.completions.create(
            model=config.MODEL,
            messages=cast(list[ChatCompletionMessageParam], message_history),
            stream=True,
        )

        try:
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    full_response += delta
                    await msg.stream_token(delta)

        except Exception as e:
            logging.exception("Error while processing stream chunks")

            msg.content += f"ERROR! Couldn't process response stream chunks: {e}"

        finally:
            await stream.close()

    except Exception as e:
        logging.exception("Error while streaming response from model")

        if full_response:
            msg.content = (
                full_response
                + f"\n\nERROR! *Response cut off: something went wrong talking to the model: {e}"
            )

        else:
            msg.content = (
                f"ERROR! Sorry, something went wrong talking to the model: {e}"
            )

    await msg.update()

    if full_response:
        message_history.append({"role": "assistant", "content": full_response})

        if len(message_history) > MAX_HISTORY_MESSAGES + 1:
            message_history = [SYSTEM_PROMPT] + message_history[-MAX_HISTORY_MESSAGES:]

        cl.user_session.set("message_history", message_history)
