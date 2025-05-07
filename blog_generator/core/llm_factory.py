# core/llm_factory.py

def get_llm_client(config):
    provider = config.get("llm_provider", "openai").lower()

    if provider == "gemini":
        from core.gemini_client import GeminiClient
        return GeminiClient(config)
    elif provider == "openai":
        from core.openai_client import OpenAIClient
        return OpenAIClient(config)
    else:
        raise ValueError(f"Unsupported llm_provider: {provider}")
