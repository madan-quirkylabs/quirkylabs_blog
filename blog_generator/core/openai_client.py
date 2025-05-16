import openai
import time
import logging
import os
from core.llm_client import LLMClient

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
