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
    Cleans and extracts a valid JSON object from a raw LLM response string.
    Strips triple backticks, language tags, and isolates the main JSON block.
    """
    # Remove markdown formatting
    cleaned = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE)

    # Extract the JSON portion
    json_match = re.search(r"{.*}", cleaned, flags=re.DOTALL)
    if not json_match:
        raise ValueError("No valid JSON object found in response.")

    return json.loads(json_match.group(0))