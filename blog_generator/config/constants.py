import os

# Utility to create folders if not exist
def ensure_directories(paths: dict):
    for key, path in paths.items():
        if "output" in key:
            os.makedirs(path, exist_ok=True)
