"""
metadata_generator.py

Module to generate SEO metadata for each blog post
using OpenAI (new OpenAI >= 1.0.0 version).

- Title
- Slug
- Meta Title
- Meta Description

Handles retries, test mode, logging, and failure recovery.

Author: QuirkyLabs
"""

import os
import sys
import time
import pandas as pd

# Project structure setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
from utils.config_manager import ConfigManager
from utils.logger_manager import LoggerManager
from utils.retry_utils import retry_with_exponential_backoff
from utils.file_helpers import load_csv, save_csv, ensure_directory
from utils.paths import METADATA_OUTPUT_DIR, KEYWORD_RANKING_OUTPUT_DIR, LOGS_OUTPUT_DIR

class MetadataGenerator:
    """
    Uses OpenAI to generate SEO blog metadata from ranked keyword suggestions.
    """

    def __init__(self):
        """
        Initialize MetadataGenerator with configs, OpenAI client, and paths.
        """
        self.config = ConfigManager()
        self.logger = LoggerManager(
            log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "metadata"),
            log_prefix="metadata_log"
        )

        self.client = OpenAI(api_key=self.config.get("OPENAI_API_KEY"))

        self.test_mode = self.config.get("TEST_MODE", True)
        self.test_limit = self.config.get("TEST_LIMIT", 5)
        self.model_name = self.config.get("OPENAI_MODEL", "gpt-4")
        self.request_delay = self.config.get("OPENAI_REQUEST_DELAY", 1)

        self.ranked_suggestions_path = os.path.join(KEYWORD_RANKING_OUTPUT_DIR, "ranked_suggestions.csv")
        self.metadata_output_path = os.path.join(METADATA_OUTPUT_DIR, "metadata_generated.csv")
        self.metadata_failed_path = os.path.join(METADATA_OUTPUT_DIR, "metadata_failed.csv")

    @retry_with_exponential_backoff(max_retries=5, initial_backoff=2)
    def call_openai(self, prompt):
        """
        Make a call to the OpenAI API with retries.

        Args:
            prompt (str): Prompt text for OpenAI.

        Returns:
            str: Content generated by OpenAI.
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a professional SEO expert and copywriter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content

    def build_prompt(self, keyword):
        """
        Build an SEO metadata generation prompt.

        Args:
            keyword (str): Keyword for metadata generation.

        Returns:
            str: Formatted prompt.
        """
        return (
            f"Generate SEO metadata for the blog topic: '{keyword}'. "
            "Return the following strictly:\n\n"
            "Title: <title>\n"
            "Slug: <slug>\n"
            "Meta Title: <meta_title>\n"
            "Meta Description: <meta_description>\n\n"
            "Constraints:\n"
            "- Title must be engaging.\n"
            "- Slug must be lowercase and hyphenated.\n"
            "- Meta Title must be <= 60 characters.\n"
            "- Meta Description must be 120–160 characters.\n"
        )

    def parse_openai_response(self, response_text):
        """
        Parse OpenAI text response into structured fields.

        Args:
            response_text (str): OpenAI response text.

        Returns:
            dict: Parsed metadata fields.
        """
        metadata = {
            "Title": "",
            "Slug": "",
            "Meta Title": "",
            "Meta Description": ""
        }

        for line in response_text.split("\n"):
            if line.lower().startswith("title:"):
                metadata["Title"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("slug:"):
                metadata["Slug"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("meta title:"):
                metadata["Meta Title"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("meta description:"):
                metadata["Meta Description"] = line.split(":", 1)[1].strip()

        return metadata

    def generate_metadata(self):
        """
        Main method to generate metadata for all ranked suggestions.
        """
        if not os.path.exists(self.ranked_suggestions_path):
            self.logger.error(f"Ranked suggestions file not found at {self.ranked_suggestions_path}")
            raise FileNotFoundError("Ranked suggestions missing.")

        df = load_csv(self.ranked_suggestions_path)

        if self.test_mode:
            self.logger.info(f"⚡ TEST MODE ENABLED: Limiting to {self.test_limit} suggestions.")
            df = df.head(self.test_limit)

        all_metadata = []
        failures = []

        for idx, row in df.iterrows():
            keyword = row['suggestion']
            prompt = self.build_prompt(keyword)

            try:
                self.logger.debug(f"Calling OpenAI for: {keyword}")
                response_text = self.call_openai(prompt)

                metadata = self.parse_openai_response(response_text)
                metadata["Original Suggestion"] = keyword

                all_metadata.append(metadata)
                self.logger.info(f"✅ Metadata generated for: {keyword}")

            except Exception as e:
                self.logger.error(f"❌ Metadata generation failed for: {keyword}", extra={"exception": str(e)})
                failures.append({"suggestion": keyword, "error": str(e)})

            time.sleep(self.request_delay)

        ensure_directory(os.path.dirname(self.metadata_output_path))
        ensure_directory(os.path.dirname(self.metadata_failed_path))

        if all_metadata:
            save_csv(pd.DataFrame(all_metadata), self.metadata_output_path)
            self.logger.info(f"✅ Metadata saved to {self.metadata_output_path}")

        if failures:
            save_csv(pd.DataFrame(failures), self.metadata_failed_path)
            self.logger.warning(f"⚠️ Metadata failures saved to {self.metadata_failed_path}")

def main():
    """
    Main runner for standalone execution.
    """
    generator = MetadataGenerator()
    generator.generate_metadata()
    generator.logger.info("🏁 Metadata generation completed successfully.")

if __name__ == "__main__":
    main()
