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
