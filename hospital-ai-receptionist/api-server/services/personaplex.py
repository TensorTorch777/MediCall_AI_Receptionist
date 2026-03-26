"""
NVIDIA PersonaPlex conversation handler via Hugging Face Inference API.

PersonaPlex is a full-duplex voice AI model. This module wraps the
Hugging Face Inference API so the rest of the codebase can call
`generate_response(user_text, context)` and get back Aria's reply.
"""
import logging
from pathlib import Path

from huggingface_hub import InferenceClient

from config import settings

logger = logging.getLogger("personaplex")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "receptionist.txt"

CHAT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

_client: InferenceClient | None = None
_system_prompt: str | None = None


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        _client = InferenceClient(
            model=CHAT_MODEL,
            token=settings.HF_API_KEY,
        )
        logger.info("HF InferenceClient initialised for %s (text fallback for PersonaPlex)", CHAT_MODEL)
    return _client


def _get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
        logger.info("Loaded persona prompt (%d chars)", len(_system_prompt))
    return _system_prompt


def generate_response(
    user_text: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Send user speech (transcribed text) to PersonaPlex via HF Inference API
    and return Aria's text reply.

    Parameters
    ----------
    user_text : str
        The latest thing the patient said.
    conversation_history : list[dict], optional
        Previous turns in OpenAI-style message format
        [{"role": "user"|"assistant", "content": "…"}, …]

    Returns
    -------
    str
        Aria's reply text.
    """
    client = _get_client()
    system_prompt = _get_system_prompt()

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat_completion(
            messages=messages,
            max_tokens=256,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        logger.info("PersonaPlex reply: %s", reply[:120])
        return reply

    except Exception as exc:
        logger.error("PersonaPlex API error: %s", exc)
        return (
            "I'm sorry, I'm having a little trouble right now. "
            "Could you repeat that for me?"
        )
