"""
config_manager.py

Purpose:
    Load and manage project-wide configuration settings from a JSON file.

Features:
    - Centralized config loading
    - Default fallback support
    - Safe reloading at runtime
    - Pretty-printing for debugging

Author: QuirkyLabs
"""

import os
import json

class ConfigManager:
    """
    Configuration Manager for the SEO Topic Generator system.
    """

    DEFAULT_CONFIG_PATH = os.path.join("config", "settings.json")

    def __init__(self, config_path=None):
        """
        Initialize ConfigManager.

        Args:
            config_path (str, optional): Custom config file path. Defaults to DEFAULT_CONFIG_PATH.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        """
        Load settings from the JSON configuration file into memory.
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"[ConfigManager] Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"[ConfigManager] Failed to parse JSON file: {e}")

    def get(self, key, default=None):
        """
        Retrieve a specific setting value safely.

        Args:
            key (str): Configuration key to retrieve.
            default (Any, optional): Default value if key not found.

        Returns:
            Any: Retrieved value or default.
        """
        return self.settings.get(key, default)

    def reload(self):
        """
        Reload the settings file without restarting the application.
        """
        self.load_settings()

    def __str__(self):
        """
        Pretty-print the loaded settings (for debugging).
        """
        return json.dumps(self.settings, indent=4, ensure_ascii=False)

# Example usage (only for local testing - comment out in production)
if __name__ == "__main__":
    config = ConfigManager()
    print(config)
