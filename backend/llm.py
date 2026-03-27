"""
LLM client initialization.

This module wraps LangChain's `ChatGoogleGenerativeAI` for Gemini 2.0 Flash.
"""

from __future__ import annotations

from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from .config import settings


def build_chat_llm() -> ChatGoogleGenerativeAI:
    """
    Construct a Gemini chat model using the configured API key.

    Returns:
        A configured `ChatGoogleGenerativeAI` instance.

    Raises:
        RuntimeError: if `GEMINI_API_KEY` is not configured.
    """

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.3,
        google_api_key=settings.GEMINI_API_KEY,
    )


chat_llm: Optional[ChatGoogleGenerativeAI]

try:
    chat_llm = build_chat_llm()
except RuntimeError:
    # Allow the API server to start without LLM credentials.
    chat_llm = None

