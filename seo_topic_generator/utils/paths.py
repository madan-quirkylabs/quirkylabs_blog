"""
paths.py

Purpose:
    Centralized manager for all important project paths.

Features:
    - Standardized folder structure
    - Easy refactoring (change once, reflected everywhere)
    - Safe directory creation utility
    - Clean separation of Inputs, Outputs, Configs

Author: QuirkyLabs
"""

import os

# --- Core Directories ---

# Project Root (dynamic, not hardcoded)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 📂 Inputs
INPUTS_DIR = os.path.join(PROJECT_ROOT, "inputs")

# 📂 Outputs
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "outputs")
SEEDS_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "seeds")
SCRAPING_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "scraping")
KEYWORD_RANKING_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "keyword_ranking")
METADATA_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "metadata")
VALIDATED_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "validated")
BLOGS_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "blogs")
LOGS_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "logs")

# 📂 Configs
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
PROMPTS_DIR = os.path.join(CONFIG_DIR, "prompts")

# --- Specific Files (Optional pre-definitions for easier access) ---

# Config files
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
POSTPROCESSING_PROMPTS_FILE = os.path.join(PROMPTS_DIR, "postprocessing_prompts.json")

# Input files
BASE_SEEDS_FILE = os.path.join(INPUTS_DIR, "base_seeds.csv")

# Output files
EXPANDED_SEEDS_FILE = os.path.join(SEEDS_OUTPUT_DIR, "expanded_seeds.csv")
SCRAPED_SUGGESTIONS_FILE = os.path.join(SCRAPING_OUTPUT_DIR, "scraped_suggestions_success.csv")
RANKED_SUGGESTIONS_FILE = os.path.join(KEYWORD_RANKING_OUTPUT_DIR, "ranked_suggestions.csv")
GENERATED_METADATA_FILE = os.path.join(METADATA_OUTPUT_DIR, "metadata_generated.csv")
VALIDATED_METADATA_FILE = os.path.join(VALIDATED_OUTPUT_DIR, "validated_metadata.csv")
REJECTED_METADATA_FILE = os.path.join(VALIDATED_OUTPUT_DIR, "rejected_metadata.csv")
FINAL_SAMPLE_INPUT_FILE = os.path.join(BLOGS_OUTPUT_DIR, "sample_input.csv")

# --- Utilities ---

def ensure_all_directories():
    """
    Create all necessary output directories if they don't exist.
    """
    directories = [
        OUTPUT_ROOT,
        SEEDS_OUTPUT_DIR,
        SCRAPING_OUTPUT_DIR,
        KEYWORD_RANKING_OUTPUT_DIR,
        METADATA_OUTPUT_DIR,
        VALIDATED_OUTPUT_DIR,
        BLOGS_OUTPUT_DIR,
        LOGS_OUTPUT_DIR
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Example Usage (only for local testing)
if __name__ == "__main__":
    print(f"✅ Project Root: {PROJECT_ROOT}")
    print(f"✅ Inputs Directory: {INPUTS_DIR}")
    print(f"✅ Outputs Directory: {OUTPUT_ROOT}")
    ensure_all_directories()
    print("✅ All directories ensured successfully.")
