# core/llm_client.py

from abc import ABC, abstractmethod
from typing import List, Dict

class LLMClient(ABC):
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate a completion from a list of messages.
        Example message: {"role": "user", "content": "Tell me a joke"}
        """
        pass
