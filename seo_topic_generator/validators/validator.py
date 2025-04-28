"""
validator.py

Purpose:
    Validate generated blog metadata for SEO compliance.

Validation Checks:
    - Title length (50–70 characters)
    - Slug format (lowercase, hyphenated, URL-safe)
    - Meta Title length (50–60 characters)
    - Meta Description length (120–160 characters)
    - Presence of all critical fields

Outputs:
    - Valid entries -> validated_metadata.csv
    - Invalid entries -> rejected_metadata.csv
    - Full structured logging

Author: QuirkyLabs
"""

import os
import sys
import re
import pandas as pd

# Ensure project root is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config_manager import ConfigManager
from utils.logger_manager import LoggerManager
from utils.file_helpers import load_csv, save_csv, ensure_directory
from utils.paths import METADATA_OUTPUT_DIR, VALIDATED_OUTPUT_DIR, LOGS_OUTPUT_DIR

class MetadataValidator:
    """
    Validates SEO metadata based on strict formatting and length rules.
    """

    def __init__(self):
        self.config = ConfigManager()
        self.logger = LoggerManager(
            log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "validation"),
            log_prefix="validation_log"
        )

        # Paths
        self.metadata_input_path = os.path.join(METADATA_OUTPUT_DIR, "metadata_generated.csv")
        self.validated_output_path = os.path.join(VALIDATED_OUTPUT_DIR, "validated_metadata.csv")
        self.rejected_output_path = os.path.join(VALIDATED_OUTPUT_DIR, "rejected_metadata.csv")

    # --- Individual Field Validators ---

    def validate_title(self, title):
        return 50 <= len(title.strip()) <= 70

    def validate_slug(self, slug):
        return bool(re.fullmatch(r"[a-z0-9\-]+", slug.strip()))

    def validate_meta_title(self, meta_title):
        return 50 <= len(meta_title.strip()) <= 60

    def validate_meta_description(self, meta_description):
        return 120 <= len(meta_description.strip()) <= 160

    # --- Full Row Validator ---

    def validate_row(self, row):
        """
        Validate a single metadata row.

        Args:
            row (pd.Series): Metadata row.

        Returns:
            bool: True if valid, else False.
        """
        required_fields = ["Title", "Slug", "Meta Title", "Meta Description"]

        if not all(row.get(field) for field in required_fields):
            return False

        return (
            self.validate_title(row["Title"]) and
            self.validate_slug(row["Slug"]) and
            self.validate_meta_title(row["Meta Title"]) and
            self.validate_meta_description(row["Meta Description"])
        )

    def validate_metadata(self):
        """
        Validate all metadata entries, split into valid and rejected files.
        """

        if not os.path.exists(self.metadata_input_path):
            self.logger.error(f"Metadata input file not found at {self.metadata_input_path}")
            raise FileNotFoundError("Metadata input missing.")

        df = load_csv(self.metadata_input_path)

        if df.empty:
            self.logger.warning("⚠️ Metadata file is empty. Nothing to validate.")
            return pd.DataFrame()

        self.logger.info(f"🔍 Starting validation for {len(df)} metadata entries...")

        valid_rows = []
        rejected_rows = []

        for idx, row in df.iterrows():
            original_suggestion = row.get('Original Suggestion', 'Unknown')

            if self.validate_row(row):
                valid_rows.append(row)
                self.logger.debug(f"✅ Valid metadata: {original_suggestion}")
            else:
                rejected_rows.append(row)
                self.logger.warning(f"❌ Invalid metadata: {original_suggestion}")

        valid_df = pd.DataFrame(valid_rows)
        rejected_df = pd.DataFrame(rejected_rows)

        ensure_directory(os.path.dirname(self.validated_output_path))
        ensure_directory(os.path.dirname(self.rejected_output_path))

        save_csv(valid_df, self.validated_output_path)
        save_csv(rejected_df, self.rejected_output_path)

        self.logger.info(f"🏆 {len(valid_df)} valid entries saved to {self.validated_output_path}")
        self.logger.warning(f"⚠️ {len(rejected_df)} invalid entries saved to {self.rejected_output_path}")

        return valid_df

# --- Entrypoint ---

def main():
    """
    Main runner to execute validator standalone.
    """
    validator = MetadataValidator()
    validated_df = validator.validate_metadata()

    if not validated_df.empty:
        print(f"✅ Metadata Validation Complete: {len(validated_df)} valid entries found.")

if __name__ == "__main__":
    main()
