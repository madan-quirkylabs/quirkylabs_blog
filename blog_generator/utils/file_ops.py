# utils/file_ops.py

import os
import shutil

def delete_file(filepath):
    """Delete a file safely."""
    if os.path.exists(filepath):
        os.remove(filepath)

def move_file(src_path, dest_path):
    """Move a file from source to destination."""
    if os.path.exists(src_path):
        shutil.move(src_path, dest_path)

def create_folder_if_missing(folder_path):
    """Create folder if it doesn't exist."""
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
