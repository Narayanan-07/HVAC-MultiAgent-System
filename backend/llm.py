"""
LLM client initialization for Gemini 2.0 Flash.
"""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.3,
    max_retries=5,
    request_timeout=120,
)