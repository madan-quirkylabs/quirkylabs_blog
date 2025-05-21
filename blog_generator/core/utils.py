# core/utils.py

import os
import shutil
import json
import re

# ------------------------------
# File Operations
# ------------------------------
def delete_file(filepath):
    if os.path.exists(filepath):
        os.remove(filepath)

def move_file(src_path, dest_path):
    if os.path.exists(src_path):
        shutil.move(src_path, dest_path)

def create_folder_if_missing(folder_path):
    os.makedirs(folder_path, exist_ok=True)

def get_section_path(slug, section_name, ext="md"):
    folder = os.path.join("output", "sections", slug)
    create_folder_if_missing(folder)
    return os.path.join(folder, f"{section_name}.{ext}")

def save_section(slug, section_name, content, ext="md"):
    path = get_section_path(slug, section_name, ext)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def load_section(slug, section_name, ext="md"):
    path = get_section_path(slug, section_name, ext)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

# ------------------------------
# Console Colors
# ------------------------------
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ------------------------------
# Directory Creation Utility
# ------------------------------
def ensure_directories(paths: dict):
    for key, path in paths.items():
        if "output" in key:
            os.makedirs(path, exist_ok=True)

def extract_json_from_response(response: str) -> dict:
    """
    Extract a valid JSON object from raw LLM response.
    Handles markdown formatting and triple backtick fences.
    """
    # Remove triple backticks and optional `json` label
    cleaned = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE)

    # Match the JSON block using a greedy matcher
    json_match = re.search(r"{.*}", cleaned, flags=re.DOTALL)
    if not json_match:
        raise ValueError("No valid JSON object found in response.")

    return json.loads(json_match.group(0))

def extract_yaml_from_response(response: str) -> str:
    """
    Extracts a valid YAML block from an LLM response enclosed in triple backticks.
    """
    # Try to find a ```yaml ... ``` fenced block
    match = re.search(r"```yaml(.*?)```", response, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("No YAML block found in response.")

    yaml_block = match.group(1).strip()
    return yaml_block

def convert_sets_to_lists(obj):
    """Recursively convert sets to lists and handle ellipsis for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_sets_to_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_sets_to_lists(item) for item in obj]
    elif isinstance(obj, set):
        return list(obj)
    elif obj is ...:
        return "..."  # or None or "Ellipsis"
    else:
        return obj
