"""
keyword_ranker.py

Module to score and rank keywords based on SEO long-tail potential.

- Long-tail scoring
- Intent detection bonus
- Structured logging
- De-duplication

Author: QuirkyLabs
"""

import os
import sys
import pandas as pd

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger_manager import LoggerManager
from utils.config_manager import ConfigManager
from utils.file_helpers import load_csv, save_csv, ensure_directory
from utils.paths import SCRAPING_OUTPUT_DIR, KEYWORD_RANKING_OUTPUT_DIR, LOGS_OUTPUT_DIR

class KeywordRanker:
    """
    Ranks scraped keyword suggestions based on their SEO quality.
    """

    INTENT_KEYWORDS = [
        "how to", "ways to", "tips for", "best", "guide to", "strategies for", "ideas for"
    ]

    def __init__(self):
        """
        Initialize the KeywordRanker with configs and paths.
        """
        self.config = ConfigManager()
        self.logger = LoggerManager(
            log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "keyword_ranking"),
            log_prefix="keyword_ranking_log"
        )

        self.scraped_suggestions_path = os.path.join(SCRAPING_OUTPUT_DIR, "scraped_suggestions_success.csv")
        self.ranked_output_path = os.path.join(KEYWORD_RANKING_OUTPUT_DIR, "ranked_suggestions.csv")

    def calculate_score(self, keyword):
        """
        Calculate an SEO score for a given keyword.

        Args:
            keyword (str): The keyword suggestion.

        Returns:
            int: SEO score.
        """
        if not keyword or not isinstance(keyword, str):
            return 0

        words = keyword.strip().split()
        word_count = len(words)
        char_count = len(keyword.strip())

        score = 0

        # Base score favors more words
        score += word_count * 2

        # Favor optimal 4-8 word range
        if 4 <= word_count <= 8:
            score += 10
        elif word_count > 12:
            score -= 5  # Penalize overly long queries

        # Intent-based bonuses
        lowered = keyword.lower()
        for marker in self.INTENT_KEYWORDS:
            if marker in lowered:
                score += 8

        # Penalize very short queries
        if char_count < 20:
            score -= 10

        return score

    def rank_keywords(self):
        """
        Rank all scraped suggestions based on SEO scoring logic.
        """
        if not os.path.exists(self.scraped_suggestions_path):
            self.logger.error(f"Scraped suggestions file not found at {self.scraped_suggestions_path}")
            raise FileNotFoundError("Scraped suggestions missing.")

        df = load_csv(self.scraped_suggestions_path)

        if df.empty:
            self.logger.warning("No suggestions available to rank.")
            return pd.DataFrame()

        df = df.drop_duplicates(subset=["suggestion"])
        df = df[df["suggestion"].notnull() & (df["suggestion"].str.strip() != "")]

        self.logger.info(f"Scoring {len(df)} unique suggestions...")

        df["seo_score"] = df["suggestion"].apply(self.calculate_score)
        df = df.sort_values(by="seo_score", ascending=False).reset_index(drop=True)

        ensure_directory(os.path.dirname(self.ranked_output_path))
        save_csv(df, self.ranked_output_path)

        self.logger.info(f"✅ Ranked suggestions saved to {self.ranked_output_path}")

        return df

def main():
    """
    Main runner for standalone execution.
    """
    ranker = KeywordRanker()
    ranked_df = ranker.rank_keywords()

    if not ranked_df.empty:
        print("\n🏆 Top 5 Ranked Suggestions:\n")
        print(ranked_df[["suggestion", "seo_score"]].head(5))

if __name__ == "__main__":
    main()
