"""
file_helpers.py

Purpose:
    Common utilities for file I/O operations like CSV reading, writing, appending,
    and safe directory creation.

Features:
    - Safe CSV load/save
    - Row-wise appending to CSV
    - Directory existence check
    - UTF-8 encoding standardization

Author: QuirkyLabs
"""

import os
import csv
import pandas as pd

def load_csv(filepath):
    """
    Load a CSV file into a pandas DataFrame.

    Args:
        filepath (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded data.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[FileHelpers] File not found: {filepath}")
    
    return pd.read_csv(filepath, encoding="utf-8")

def save_csv(dataframe, filepath):
    """
    Save a pandas DataFrame to a CSV file.

    Args:
        dataframe (pd.DataFrame): Data to save.
        filepath (str): Destination path.
    """
    ensure_directory(os.path.dirname(filepath))
    dataframe.to_csv(filepath, index=False, encoding="utf-8")

def append_row_to_csv(filepath, row_dict, headers=None):
    """
    Append a single dictionary row to a CSV file.

    Args:
        filepath (str): Path to the CSV file.
        row_dict (dict): Row data as a dictionary.
        headers (list, optional): List of headers/columns. If None, inferred from row_dict.
    """
    ensure_directory(os.path.dirname(filepath))

    file_exists = os.path.isfile(filepath)

    with open(filepath, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers or row_dict.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(row_dict)

def ensure_directory(directory_path):
    """
    Ensure that a directory exists; create it if it does not.

    Args:
        directory_path (str): Directory path to create if missing.
    """
    if directory_path and not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
