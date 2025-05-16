import os
from core.openai_client import OpenAIClient
from core.gemini_client import GeminiClient
from config.config_loader import load_config

# Load shared config
_config = load_config()
_section_defaults = _config.get("llm_section_defaults", {})

# Instantiate both clients once
_clients = {
    "openai": OpenAIClient(_config),
    "gemini": GeminiClient(_config),
}

def call_llm(messages, section=None, provider=None, model=None, temperature=None):
    """
    Calls the appropriate LLM client with optional overrides per call or per section config.

    Args:
        messages (list): List of messages for chat completion.
        section (str): Optional section name to load default config.
        provider (str): 'openai' or 'gemini'. Overrides section config.
        model (str): Optional model override.
        temperature (float): Optional temperature override.

    Returns:
        str: The generated LLM response content.
    """
    config = _section_defaults.get(section, {}) if section else {}
    provider = provider or config.get("provider", "openai")
    model = model or config.get("model")
    temperature = temperature if temperature is not None else config.get("temperature")

    if provider not in _clients:
        raise ValueError(f"Unsupported provider: {provider}")

    override = {}
    if model:
        override["model"] = model
    if temperature is not None:
        override["temperature"] = temperature

    return _clients[provider].chat_completion(messages, override=override)

# ✅ Example usage (in generate_landing_pages.py):
# response = call_llm(messages, section="story_part_1")
# This will use the config from settings.yaml → llm_section_defaults.story_part_1

# 🧠 Next step:
# Replace all llm_client.chat_completion(...) in generate_landing_pages.py with call_llm(..., section=...)
