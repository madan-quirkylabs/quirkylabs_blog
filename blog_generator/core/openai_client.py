import openai
import time
import logging
from typing import List, Dict

class OpenAIClient:
    def __init__(self, config: dict):
        self.model = config["openai"]["model"]
        self.temperature = config["openai"]["temperature"]
        self.max_retries = config["openai"]["max_retries"]
        self.timeout = config["openai"]["request_timeout"]

    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Calls OpenAI's GPT API with retries and exponential backoff.

        Args:
            messages (List[Dict[str, str]]): List of message dictionaries to send to the model.

        Returns:
            str: The result from OpenAI's API (response message).
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logging.info(f"[OpenAI] Attempt {attempt} for prompt...")

                # Updated API call for GPT-4 or other models
                response = openai.Completion.create(
                    model=self.model,  # Use model from configuration
                    prompt=messages,  # Use the 'messages' passed in as prompt
                    temperature=self.temperature,
                    max_tokens=300,  # Optionally, adjust max tokens based on your needs
                    timeout=self.timeout,
                )

                # Return the generated content from the API
                return response.choices[0].text.strip()

            except Exception as e:
                logging.warning(f"[OpenAI Error] Attempt {attempt}: {e}")

                # Exponential backoff: retry after increasing delay
                if attempt < self.max_retries:
                    delay = 2 ** attempt  # Exponential backoff (1s, 2s, 4s, etc.)
                    logging.info(f"[OpenAI Retry] Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error("[OpenAI] Maximum retry attempts reached. Failing.")
                    raise  # Raise the error after the maximum retries

