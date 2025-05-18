import os
from core.openai_client import OpenAIClient
from core.gemini_client import GeminiClient

from core.openai_client import OpenAIClient
from core.gemini_client import GeminiClient

def call_llm(messages, section=None, provider=None, model=None, temperature=None, section_config=None):
    config = section_config or {}

    provider = provider or config.get("provider", "openai")
    model = model or config.get("model")
    temperature = temperature if temperature is not None else config.get("temperature")

    if provider == "openai":
        client = OpenAIClient({"model": model, "temperature": temperature})
    elif provider == "gemini":
        client = GeminiClient({"model": model, "temperature": temperature})
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return client.chat_completion(messages, override={"model": model, "temperature": temperature})
