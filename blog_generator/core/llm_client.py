# core/llm_client.py

from abc import ABC, abstractmethod
from typing import List, Dict

class LLMClient(ABC):
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], override: dict = None) -> str:
        pass
