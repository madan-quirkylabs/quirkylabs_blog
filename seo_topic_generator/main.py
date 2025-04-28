"""
main.py

Purpose:
    Master orchestrator for the full SEO Blog Topic Generator Pipeline.

Pipeline Steps:
    1. Expand base seeds
    2. Scrape autocomplete suggestions
    3. Rank keywords
    4. Generate SEO metadata
    5. Validate metadata
    6. Write final sample input CSV

Features:
    - Centralized logging
    - Config-driven settings
    - Fail-safe error handling
    - Timestamped execution reporting

Author: QuirkyLabs
"""

import os
import sys
import time

# Add project root for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import modules
from seeds.seed_expander import SeedExpander
from scrapers.autocomplete_scraper import AutocompleteScraper
from generators.keyword_ranker import KeywordRanker
from generators.metadata_generator import MetadataGenerator
from validators.validator import MetadataValidator
from generators.output_writer import OutputWriter

from utils.logger_manager import LoggerManager
from utils.config_manager import ConfigManager
from utils.paths import LOGS_OUTPUT_DIR

def main():
    """
    Full end-to-end orchestrator for the SEO Blog Topic Generator system.
    """

    # Setup
    logger = LoggerManager(
        log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "orchestration"),
        log_prefix="orchestration_log"
    )
    config = ConfigManager()

    logger.info("🚀 Starting SEO Blog Topic Generation Pipeline...")

    try:
        # Step 1: Expand Seeds
        logger.info("🔹 Step 1: Expanding Base Seeds...")
        expander = SeedExpander()
        expanded_df = expander.expand_seeds()
        expander.save_expanded_seeds(expanded_df)
        logger.info(f"✅ Step 1 Completed: {len(expanded_df)} expanded seeds generated.")

        # Step 2: Scrape Autocomplete Suggestions
        logger.info("🔹 Step 2: Scraping Google Autocomplete Suggestions...")
        scraper = AutocompleteScraper()
        suggestions_list = scraper.scrape()
        scraper.save_results(suggestions_list)
        logger.info(f"✅ Step 2 Completed: {len(suggestions_list)} suggestions scraped.")

        # Step 3: Rank Keywords
        logger.info("🔹 Step 3: Ranking Keywords...")
        ranker = KeywordRanker()
        ranked_df = ranker.rank_keywords()
        logger.info(f"✅ Step 3 Completed: {len(ranked_df)} keywords ranked.")

        # Step 4: Generate Metadata
        logger.info("🔹 Step 4: Generating SEO Metadata...")
        generator = MetadataGenerator()
        generator.generate_metadata()
        logger.info("✅ Step 4 Completed: Metadata generation completed.")

        # Step 5: Validate Metadata
        logger.info("🔹 Step 5: Validating Metadata...")
        validator = MetadataValidator()
        validated_df = validator.validate_metadata()
        logger.info(f"✅ Step 5 Completed: {len(validated_df)} entries validated.")

        # 🚨 Insert this BEFORE Step 6
        if validated_df.empty:
            logger.warning("⚠️ No valid metadata entries found after validation. Skipping output writing step.")
            logger.info("🏁 Pipeline Stopped Early After Validation Due to No Valid Entries.")
            return  # Exit gracefully

        # Step 6: Write Final Sample Input
        logger.info("🔹 Step 6: Writing Final Sample Input CSV...")
        writer = OutputWriter()
        writer.generate_sample_input()
        logger.info("✅ Step 6 Completed: Final sample input file created.")

    except Exception as e:
        logger.error(f"🔥 Critical Error in Pipeline: {str(e)}")
        raise

    logger.info("🏁 SEO Blog Topic Generation Pipeline Finished Successfully!")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"🏎️ Pipeline completed in {elapsed_time:.2f} seconds.")
