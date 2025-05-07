from core.llm_client import LLMClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_vertexai import ChatVertexAI

class GeminiClient(LLMClient):
    def __init__(self, config):
        gemini_config = config.get("gemini", {})
        self.model = gemini_config.get("model", "gemini-2.0-flash")
        self.temperature = gemini_config.get("temperature", 0.7)
        self.location = gemini_config.get("location", "us-central1")

        self.chat = ChatVertexAI(
            model=self.model,
            temperature=self.temperature,
            location=self.location,
            convert_system_message_to_human=True,
        )

    def chat_completion(self, messages):
        # Convert standard OpenAI-style messages into LangChain format
        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            elif m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
            else:
                raise ValueError(f"Unsupported role: {m['role']}")

        # Invoke Gemini via LangChain
        response = self.chat.invoke(lc_messages)
        return response.content.strip() if hasattr(response, "content") else str(response)
