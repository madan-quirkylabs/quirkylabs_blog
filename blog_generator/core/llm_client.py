# core/llm_clients.py

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict

import openai
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_vertexai import ChatVertexAI

# ------------------------------
# Abstract Base Class
# ------------------------------
class LLMClient(ABC):
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], override: dict = None) -> str:
        pass

# ------------------------------
# OpenAI Client
# ------------------------------
class OpenAIClient(LLMClient):
    def __init__(self, config):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = config.get("model", "gpt-4")
        self.default_temperature = config.get("temperature", 0.7)
        self.max_retries = config.get("max_retries", 3)
        self.timeout = config.get("request_timeout", 30)
        self.max_token_size = config.get("max_token_size", 2048)

        openai.api_key = self.api_key
        self.client = openai

    def chat_completion(self, messages, override=None):
        override = override or {}
        model = override.get("model", self.default_model)
        temperature = override.get("temperature", self.default_temperature)

        for attempt in range(1, self.max_retries + 1):
            try:
                logging.info(f"[OpenAI] Attempt {attempt} using model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=self.max_token_size
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                logging.warning(f"[OpenAI Error] Attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    delay = 2 ** attempt
                    logging.info(f"[OpenAI Retry] Waiting {delay}s...")
                    time.sleep(delay)
                else:
                    logging.error("[OpenAI] Max retries reached.")
                    raise

# ------------------------------
# Gemini Client
# ------------------------------
class GeminiClient(LLMClient):
    def __init__(self, config):
        self.default_model = config.get("model", "gemini-1.5-flash")
        self.default_temperature = config.get("temperature", 0.7)
        self.location = config.get("location", "us-central1")

    def chat_completion(self, messages, override=None):
        override = override or {}
        model = override.get("model", self.default_model)
        temperature = override.get("temperature", self.default_temperature)

        chat = ChatVertexAI(
            model=model,
            temperature=temperature,
            location=self.location,
            convert_system_message_to_human=True,
        )

        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            elif m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
            else:
                raise ValueError(f"Unsupported role: {m['role']}")

        response = chat.invoke(lc_messages)
        return response.content.strip() if hasattr(response, "content") else str(response)

# ------------------------------
# Factory + Router
# ------------------------------
def get_llm_client(config):
    provider = config.get("llm_provider", "openai").lower()

    if provider == "gemini":
        return GeminiClient(config)
    elif provider == "openai":
        return OpenAIClient(config)
    else:
        raise ValueError(f"Unsupported llm_provider: {provider}")

def call_llm(messages, section=None, provider=None, model=None, temperature=None, section_config=None):
    config = section_config or {}

    provider = provider or config.get("llm_provider", "openai")
    provider_cfg = config.get(provider, {})

    model = model or provider_cfg.get("model")
    temperature = temperature if temperature is not None else provider_cfg.get("temperature", 0.7)

    if provider == "openai":
        client = OpenAIClient({
            "model": model,
            "temperature": temperature,
            "max_retries": provider_cfg.get("max_retries", 3),
            "request_timeout": provider_cfg.get("request_timeout", 30),
            "max_token_size": provider_cfg.get("max_token_size", 2048)
        })
    elif provider == "gemini":
        client = GeminiClient({
            "model": model,
            "temperature": temperature,
            "location": provider_cfg.get("location", "us-central1")
        })
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return client.chat_completion(messages, override={"model": model, "temperature": temperature})
