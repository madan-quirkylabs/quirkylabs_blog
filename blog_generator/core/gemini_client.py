# core/gemini_client.py

from core.llm_client import LLMClient
from typing import List, Dict

class GeminiClient(LLMClient):
    def __init__(self, config):
        self.config = config
        # Placeholder: you can later initialize Gemini API key or client here

    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        # 🧪 Stub implementation
        print("⚠️ GeminiClient.chat_completion() called – returning dummy response.")
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "Hello!")
        return f"(Gemini says...) {last_user_msg[::-1]}"  # just returns the reversed user message
