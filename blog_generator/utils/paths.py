import os

# Resolve project root dynamically
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# INPUT and CONFIG
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
PROMPTS_DIR = os.path.join(CONFIG_DIR, "prompts")

# OUTPUT folders
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SUCCESS_DIR = os.path.join(OUTPUT_DIR, "success")
FAILURE_DIR = os.path.join(OUTPUT_DIR, "failure")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
RETRIES_DIR = os.path.join(OUTPUT_DIR, "retries")
PERMANENT_FAILURE_DIR = os.path.join(OUTPUT_DIR, "failure")

# Important config file paths
SECTION_PROMPTS_PATH = os.path.join(PROMPTS_DIR, "section_prompts.json")
PILLAR_CONFIG_PATH = os.path.join(PROMPTS_DIR, "pillar_config.json")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.yaml")

# 🛠️ Auto-create output directories (only for OUTPUT folders)
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, RETRIES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ✅ Debug print to confirm paths are loaded correctly
print(f"[Paths] Project root set to: {PROJECT_ROOT}")
print(f"[Paths] Output directories ensured at: {OUTPUT_DIR}")
