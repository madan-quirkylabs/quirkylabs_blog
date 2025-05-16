from core.llm_client import LLMClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_vertexai import ChatVertexAI

class GeminiClient(LLMClient):
    def __init__(self, config):
        self.default_model = config.get("model", "gemini-1.5-flash")
        self.default_temperature = config.get("temperature", 0.7)
        self.location = config.get("location", "us-central1")

    def chat_completion(self, messages, override=None):
        override = override or {}
        model = override.get("model", self.default_model)
        temperature = override.get("temperature", self.default_temperature)

        # Create a temporary chat instance for the specified model and temperature
        chat = ChatVertexAI(
            model=model,
            temperature=temperature,
            location=self.location,
            convert_system_message_to_human=True,
        )

        # Convert OpenAI-style messages to LangChain format
        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            elif m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
            else:
                raise ValueError(f"Unsupported role: {m['role']}")

        # Generate and return response
        response = chat.invoke(lc_messages)
        return response.content.strip() if hasattr(response, "content") else str(response)