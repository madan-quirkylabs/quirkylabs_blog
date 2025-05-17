# core/config.py

import os
import yaml
import json

# ------------------------------
# Project Root & Paths
# ------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Input & Config
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
PROMPTS_DIR = os.path.join(CONFIG_DIR, "prompts")

# Output folders
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SUCCESS_DIR = os.path.join(OUTPUT_DIR, "success")
FAILURE_DIR = os.path.join(OUTPUT_DIR, "failure")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
RETRIES_DIR = os.path.join(OUTPUT_DIR, "retries")
PERMANENT_FAILURE_DIR = os.path.join(OUTPUT_DIR, "failure")

# Important config file paths
SECTION_PROMPTS_PATH = os.path.join(PROMPTS_DIR, "section_prompts.yaml")
PILLAR_CONFIG_PATH = os.path.join(PROMPTS_DIR, "pillar_config.json")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.yaml")

# ------------------------------
# Config Loaders
# ------------------------------
def load_config(path=SETTINGS_PATH) -> dict:
    with open(path, "r") as file:
        config = yaml.safe_load(file)

    # Inject resolved paths for convenience
    config['paths'] = {
        'input_csv': os.path.join(INPUT_DIR, "sample_input.csv"),
        'success_dir': SUCCESS_DIR,
        'failure_dir': FAILURE_DIR,
        'logs_dir': LOGS_DIR,
        'retries_dir': RETRIES_DIR,
        'permanent_failure_dir': PERMANENT_FAILURE_DIR,
    }
    return config

def load_pillar_config(path=PILLAR_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ------------------------------
# Debug Confirmation
# ------------------------------
if __name__ == "__main__":
    print(f"[Paths] Project root: {PROJECT_ROOT}")
    print(f"[Paths] Output directories initialized at: {OUTPUT_DIR}")
