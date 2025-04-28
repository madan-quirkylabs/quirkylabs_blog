"""
seed_expander.py

Purpose:
    Expands base seeds into richer, more detailed long-tail search phrases.

Features:
    - Structured logging
    - Config-driven test mode
    - Pattern-based expansion
    - Safe directory handling

Author: QuirkyLabs
"""

import os
import sys
import random
import pandas as pd

# Ensure project root is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config_manager import ConfigManager
from utils.logger_manager import LoggerManager
from utils.file_helpers import load_csv, save_csv, ensure_directory
from utils.paths import INPUTS_DIR, SEEDS_OUTPUT_DIR, LOGS_OUTPUT_DIR

class SeedExpander:
    """
    Expands base seeds into richer, long-tail search phrases using predefined patterns.
    """

    DEFAULT_PATTERNS = [
        "how to manage {seed}",
        "tips to overcome {seed}",
        "why does {seed} happen",
        "best strategies for {seed}",
        "common problems with {seed}",
        "ways to solve {seed}",
        "what causes {seed}",
        "signs of {seed}",
        "can {seed} be treated",
        "simple hacks for {seed}"
    ]

    def __init__(self):
        """
        Initialize SeedExpander.
        """
        self.config = ConfigManager()
        self.logger = LoggerManager(
            log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "seed_expansion"),
            log_prefix="seed_expansion_log"
        )

        # Paths
        self.base_seeds_path = os.path.join(INPUTS_DIR, "base_seeds.csv")
        self.expanded_seeds_output_path = os.path.join(SEEDS_OUTPUT_DIR, "expanded_seeds.csv")

        # Config values
        self.test_mode = self.config.get("TEST_MODE", True)
        self.test_limit = self.config.get("TEST_LIMIT", 5)

    def expand_patterns(self, base_seed):
        """
        Expand a single base seed into multiple variations.

        Args:
            base_seed (str): The base keyword.

        Returns:
            list: List of expanded search phrases.
        """
        expanded = [pattern.format(seed=base_seed) for pattern in self.DEFAULT_PATTERNS]
        random.shuffle(expanded)
        return expanded

    def expand_seeds(self):
        """
        Expand all base seeds into richer variations.

        Returns:
            pd.DataFrame: DataFrame of expanded seeds.
        """
        if not os.path.exists(self.base_seeds_path):
            self.logger.error(f"Base seeds file not found at {self.base_seeds_path}")
            raise FileNotFoundError("Base seeds file missing.")

        base_seeds_df = load_csv(self.base_seeds_path)

        if base_seeds_df.empty:
            self.logger.warning("Base seeds file is empty. Nothing to expand.")
            return pd.DataFrame()

        if self.test_mode:
            self.logger.info(f"⚡ TEST MODE: Expanding only {self.test_limit} seeds.")
            base_seeds_df = base_seeds_df.head(self.test_limit)

        self.logger.info(f"🔄 Starting expansion for {len(base_seeds_df)} base seeds...")

        expanded_records = []

        for idx, row in base_seeds_df.iterrows():
            base_seed = row.get("base_seed")
            if not base_seed or not isinstance(base_seed, str):
                self.logger.warning(f"⚠️ Invalid base seed at row {idx}. Skipping.")
                continue

            phrases = self.expand_patterns(base_seed)
            for phrase in phrases:
                expanded_records.append({
                    "expanded_seed": phrase,
                    "base_seed": base_seed,
                    "expansion_method": "pattern",
                    "status": "ready"
                })

        self.logger.info(f"✅ Generated {len(expanded_records)} expanded seeds.")

        return pd.DataFrame(expanded_records)

    def save_expanded_seeds(self, expanded_df):
        """
        Save expanded seeds to the output file.

        Args:
            expanded_df (pd.DataFrame): DataFrame of expanded seeds.
        """
        if expanded_df.empty:
            self.logger.warning("⚠️ No expanded seeds to save.")
            return

        ensure_directory(os.path.dirname(self.expanded_seeds_output_path))
        save_csv(expanded_df, self.expanded_seeds_output_path)

        self.logger.info(f"✅ Expanded seeds saved to {self.expanded_seeds_output_path}")

def main():
    """
    Main runner for seed expansion standalone.
    """
    expander = SeedExpander()
    expanded_df = expander.expand_seeds()
    expander.save_expanded_seeds(expanded_df)

if __name__ == "__main__":
    main()
