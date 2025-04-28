"""
output_writer.py

Module to create the final sample_input.csv
from validated metadata.

- No OpenAI calls
- Structured logging
- Config-driven settings
- Timestamped outputs

Author: QuirkyLabs
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config_manager import ConfigManager
from utils.logger_manager import LoggerManager
from utils.file_helpers import load_csv, save_csv, ensure_directory
from utils.paths import VALIDATED_OUTPUT_DIR, BLOGS_OUTPUT_DIR, LOGS_OUTPUT_DIR

class OutputWriter:
    """
    Converts validated metadata into the final sample input format for the blog generator.
    """

    def __init__(self):
        """
        Initialize OutputWriter with configuration and logger.
        """
        self.config = ConfigManager()
        self.logger = LoggerManager(
            log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "output_writer"),
            log_prefix="output_writer_log"
        )

        # Paths
        self.validated_metadata_path = os.path.join(VALIDATED_OUTPUT_DIR, "validated_metadata.csv")
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.final_output_path = os.path.join(BLOGS_OUTPUT_DIR, f"sample_input_{timestamp}.csv")

        self.test_mode = self.config.get("TEST_MODE", True)
        self.test_limit = self.config.get("TEST_LIMIT", 5)

    def prepare_final_dataframe(self, validated_df):
        """
        Reformat validated metadata into the expected final structure.

        Args:
            validated_df (pd.DataFrame): DataFrame of validated metadata.

        Returns:
            pd.DataFrame: Structured DataFrame ready for blog generator input.
        """
        required_columns = ["Topic", "Slug", "Meta Title", "Meta Description", "Primary Keyword"]
        final_records = []

        for _, row in validated_df.iterrows():
            record = {
                "Topic": row.get("Original Suggestion", "").title(),
                "Slug": row.get("Slug", ""),
                "Meta Title": row.get("Meta Title", ""),
                "Meta Description": row.get("Meta Description", ""),
                "Primary Keyword": row.get("Original Suggestion", "").lower()
            }
            final_records.append(record)

        return pd.DataFrame(final_records, columns=required_columns)

    def generate_sample_input(self):
        """
        Main runner to generate sample_input.csv from validated metadata.
        """
        if not os.path.exists(self.validated_metadata_path):
            self.logger.error(f"Validated metadata file not found at {self.validated_metadata_path}")
            raise FileNotFoundError("Validated metadata missing.")

        validated_df = load_csv(self.validated_metadata_path)

        if validated_df.empty:
            self.logger.warning("Validated metadata file is empty. Nothing to write.")
            return

        if self.test_mode:
            self.logger.info(f"⚡ TEST MODE ENABLED: Limiting to {self.test_limit} entries.")
            validated_df = validated_df.head(self.test_limit)

        final_df = self.prepare_final_dataframe(validated_df)

        if final_df.empty:
            self.logger.warning("⚠️ No valid entries found after formatting. Output will not be generated.")
            return

        ensure_directory(os.path.dirname(self.final_output_path))
        save_csv(final_df, self.final_output_path)

        self.logger.info(f"✅ Final sample_input.csv saved to {self.final_output_path}")
        print(f"🏁 Final sample_input.csv generated successfully.")

def main():
    """
    Entry point to run OutputWriter standalone.
    """
    writer = OutputWriter()
    writer.generate_sample_input()

if __name__ == "__main__":
    main()
