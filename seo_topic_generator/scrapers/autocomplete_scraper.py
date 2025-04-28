"""
autocomplete_scraper.py

Purpose:
    Scrapes Google Autocomplete suggestions for expanded seeds.

Features:
    - Structured logging
    - Retry with exponential backoff
    - Test mode support
    - Config-driven settings

Author: QuirkyLabs
"""

import os
import sys
import time
import requests
import pandas as pd

# Ensure project root is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config_manager import ConfigManager
from utils.logger_manager import LoggerManager
from utils.retry_utils import retry_with_exponential_backoff
from utils.file_helpers import load_csv, save_csv, ensure_directory
from utils.paths import SEEDS_OUTPUT_DIR, SCRAPING_OUTPUT_DIR, LOGS_OUTPUT_DIR

class AutocompleteScraper:
    """
    Scrapes Google Autocomplete suggestions for expanded seeds.
    """

    def __init__(self):
        """
        Initialize scraper with config and logger.
        """
        self.config = ConfigManager()
        self.logger = LoggerManager(
            log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "scraping"),
            log_prefix="scraping_log"
        )

        # Paths
        self.expanded_seeds_path = os.path.join(SEEDS_OUTPUT_DIR, "expanded_seeds.csv")
        self.success_output_path = os.path.join(SCRAPING_OUTPUT_DIR, "scraped_suggestions_success.csv")
        self.failed_output_path = os.path.join(SCRAPING_OUTPUT_DIR, "scraped_suggestions_failed.csv")

        # Config values
        self.request_delay = self.config.get("REQUEST_DELAY", 1.5)
        self.test_mode = self.config.get("TEST_MODE", True)
        self.test_limit = self.config.get("TEST_LIMIT", 5)

        # Google Autocomplete API endpoint
        self.autocomplete_url = "https://suggestqueries.google.com/complete/search"

    @retry_with_exponential_backoff(max_retries=5, initial_backoff=2)
    def fetch_suggestions(self, query):
        """
        Fetch autocomplete suggestions for a given query.

        Args:
            query (str): Seed query string.

        Returns:
            list: List of suggestion strings.
        """
        params = {
            "client": "firefox",
            "q": query
        }
        response = requests.get(self.autocomplete_url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()[1]

    def scrape(self):
        """
        Scrape autocomplete suggestions for all expanded seeds.

        Returns:
            list: List of suggestion records.
        """
        if not os.path.exists(self.expanded_seeds_path):
            self.logger.error(f"Expanded seeds file not found at {self.expanded_seeds_path}")
            raise FileNotFoundError("Expanded seeds file missing.")

        expanded_seeds_df = load_csv(self.expanded_seeds_path)

        if expanded_seeds_df.empty:
            self.logger.warning("Expanded seeds file is empty. No seeds to scrape.")
            return []

        if self.test_mode:
            self.logger.info(f"⚡ TEST MODE: Limiting to {self.test_limit} seeds.")
            expanded_seeds_df = expanded_seeds_df.head(self.test_limit)

        self.logger.info(f"🔄 Starting scraping for {len(expanded_seeds_df)} seeds...")

        suggestions_list = []

        for _, row in expanded_seeds_df.iterrows():
            seed = row['expanded_seed']

            try:
                self.logger.debug(f"Fetching suggestions for: {seed}")

                suggestions = self.fetch_suggestions(seed)

                if suggestions:
                    for suggestion in suggestions:
                        suggestions_list.append({
                            "expanded_seed": seed,
                            "suggestion": suggestion,
                            "status": "success"
                        })
                    self.logger.info(f"✅ {len(suggestions)} suggestions fetched for seed: {seed}")
                else:
                    self.logger.warning(f"⚠️ No suggestions found for seed: {seed}")
                    suggestions_list.append({
                        "expanded_seed": seed,
                        "suggestion": "",
                        "status": "fail"
                    })

            except Exception as e:
                self.logger.error(f"❌ Failed to fetch suggestions for seed: {seed}", extra={"exception": str(e)})
                suggestions_list.append({
                    "expanded_seed": seed,
                    "suggestion": "",
                    "status": "fail"
                })

            # Respect Google's rate limiting policies
            time.sleep(self.request_delay)

        return suggestions_list

    def save_results(self, suggestions_list):
        """
        Save the successful and failed suggestions separately.

        Args:
            suggestions_list (list): List of suggestion records.
        """
        suggestions_df = pd.DataFrame(suggestions_list)

        success_df = suggestions_df[suggestions_df['status'] == 'success']
        failed_df = suggestions_df[suggestions_df['status'] == 'fail']

        ensure_directory(os.path.dirname(self.success_output_path))
        ensure_directory(os.path.dirname(self.failed_output_path))

        save_csv(success_df, self.success_output_path)
        save_csv(failed_df, self.failed_output_path)

        self.logger.info(f"✅ {len(success_df)} successful suggestions saved.")
        self.logger.warning(f"⚠️ {len(failed_df)} failed seeds saved.")

def main():
    """
    Main orchestrator to run scraper standalone.
    """
    scraper = AutocompleteScraper()
    suggestions = scraper.scrape()
    scraper.save_results(suggestions)
    scraper.logger.info("🏁 Scraping completed successfully.")

if __name__ == "__main__":
    main()
