"""Chainlit chat UI: invokes the agent on user messages with streaming."""
import sys
import time
import uuid
from pathlib import Path

# Ensure project root is on path when running as: chainlit run ui/app.py
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import chainlit as cl

from app.agent import invoke_stream, get_model_name
from app.logging_utils import log_query_answer


@cl.on_chat_start
async def on_chat_start():
    """Confirm WebSocket session is active."""
    await cl.Message(
        content="Hello! Ask me about cancer gene targets and expression (e.g. lung, breast)."
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    query = (message.content or "").strip()
    if not query:
        await cl.Message(content="Please enter a question.").send()
        return
    
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    
    # Create message that will be streamed to
    msg = cl.Message(content="")
    await msg.send()
    
    answer = ""
    try:
        # Stream the response token by token for better UX
        async for chunk in invoke_stream(query):
            answer += chunk
            msg.content = answer
            await msg.update()
    except Exception as e:
        err = str(e)
        answer = f"Error: {err}"
        if "connection" in err.lower() or "refused" in err.lower():
            answer = (
                "Cannot reach the language model. Ensure Ollama is running and the model is pulled: "
                "`docker compose run ollama ollama pull llama3.2:1b`"
            )
        msg.content = answer
        await msg.update()
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        log_query_answer(
            query=query,
            answer=answer,
            model=get_model_name(),
            request_id=request_id,
            latency_ms=latency_ms,
        )
