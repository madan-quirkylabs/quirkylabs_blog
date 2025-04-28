"""
post_processor.py

Purpose:
    Converts scraped autocomplete suggestions into structured blog metadata
    using AI-powered atomic API calls (Title, Meta Description, Keywords).

Features:
    - Separate API call per blog field
    - Rate limiting after each call
    - Exponential backoff on failures
    - Failure logging
    - Modular prompt JSON loading

Author: QuirkyLabs
"""

import os
import sys
import time
import json
import re
import pandas as pd

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
from utils.config_manager import ConfigManager
from utils.logger_manager import LoggerManager
from utils.retry_utils import retry_with_exponential_backoff
from utils.file_helpers import load_csv, save_csv, ensure_directory, append_row_to_csv
from utils.paths import SCRAPING_OUTPUT_DIR, BLOGS_OUTPUT_DIR, LOGS_OUTPUT_DIR, PROMPTS_DIR

# Load configuration
config = ConfigManager()
logger = LoggerManager(
    log_folder_path=os.path.join(LOGS_OUTPUT_DIR, "post_processor"),
    log_prefix="post_processor_log"
)

# Paths
SCRAPED_SUCCESS_PATH = os.path.join(SCRAPING_OUTPUT_DIR, "scraped_suggestions_success.csv")
BLOG_METADATA_OUTPUT_PATH = os.path.join(BLOGS_OUTPUT_DIR, "sample_input.csv")
POSTPROCESSING_FAILURE_LOG = os.path.join(LOGS_OUTPUT_DIR, "postprocessing_failures.csv")
PROMPT_JSON_PATH = os.path.join(PROMPTS_DIR, "postprocessing_prompts.json")

# Constants
RATE_LIMIT_DELAY_SECONDS = config.get("RATE_LIMIT_DELAY_SECONDS", 0.2)
RETRY_BACKOFF_INITIAL_DELAY = config.get("RETRY_BACKOFF_INITIAL_DELAY", 1)
MAX_RETRIES = config.get("MAX_RETRIES", 3)
OPENAI_MODEL = config.get("OPENAI_MODEL", "gpt-4")

# OpenAI client
openai_client = OpenAI(api_key=config.get("OPENAI_API_KEY"))

def clean_text_for_slug(text):
    """
    Converts a text string into a clean URL-friendly slug.
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text.strip('-')

@retry_with_exponential_backoff(max_retries=MAX_RETRIES, initial_backoff=RETRY_BACKOFF_INITIAL_DELAY)
def call_openai_api(prompt, instruction, field_name):
    """
    Make an OpenAI call with retry logic.

    Args:
        prompt (str): User prompt
        instruction (str): System instruction
        field_name (str): Metadata field being generated (Title, Meta Description, Keywords)

    Returns:
        str: Response content
    """
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    time.sleep(RATE_LIMIT_DELAY_SECONDS)
    return response.choices[0].message.content.strip()

def process_suggestions(scraped_df, prompt_templates):
    """
    Process raw suggestions into structured blog metadata.

    Args:
        scraped_df (pd.DataFrame): Scraped suggestions.
        prompt_templates (dict): Templates for title, meta description, keywords.

    Returns:
        pd.DataFrame: Final blog metadata entries.
    """
    records = []

    logger.info(f"🔄 Processing {len(scraped_df)} suggestions into blog metadata...")

    for _, row in scraped_df.iterrows():
        suggestion = row['suggestion']
        logger.info(f"🌱 Processing: {suggestion}")

        try:
            title_prompt = f"Suggestion: \"{suggestion}\"\n\n{prompt_templates['title_generation']['format']}"
            title = call_openai_api(title_prompt, prompt_templates['title_generation']['instruction'], "Title")

            meta_description_prompt = f"Suggestion: \"{suggestion}\"\n\n{prompt_templates['meta_description_generation']['format']}"
            meta_description = call_openai_api(meta_description_prompt, prompt_templates['meta_description_generation']['instruction'], "Meta Description")

            keywords_prompt = f"Suggestion: \"{suggestion}\"\n\n{prompt_templates['keywords_generation']['format']}"
            keywords = call_openai_api(keywords_prompt, prompt_templates['keywords_generation']['instruction'], "Keywords")

            if all([title, meta_description, keywords]):
                topic = suggestion.title()
                slug = clean_text_for_slug(topic)
                primary_keyword = suggestion.lower()

                records.append({
                    "Topic": topic,
                    "Primary Keyword": primary_keyword,
                    "Meta Title": title.replace("Title:", "").strip(),
                    "Meta Description": meta_description.replace("Meta Description:", "").strip(),
                    "Slug": slug,
                    "Keywords": keywords.replace("Keywords:", "").strip()
                })
            else:
                raise ValueError("Incomplete fields received from OpenAI")

        except Exception as e:
            logger.error(f"❌ Processing failed for: {suggestion}", extra={"exception": str(e)})
            append_row_to_csv(POSTPROCESSING_FAILURE_LOG, {
                "suggestion": suggestion,
                "title_success": bool('title' in locals() and title),
                "meta_description_success": bool('meta_description' in locals() and meta_description),
                "keywords_success": bool('keywords' in locals() and keywords)
            })

    logger.info(f"✅ Successfully processed {len(records)} blog entries.")
    return pd.DataFrame(records)

def main():
    """
    Main orchestrator to generate blog metadata from scraped suggestions.
    """
    logger.info("🚀 Starting Post-Processor...")

    ensure_directory(os.path.dirname(BLOG_METADATA_OUTPUT_PATH))
    ensure_directory(os.path.dirname(POSTPROCESSING_FAILURE_LOG))

    logger.info(f"📂 Loading prompt templates from {PROMPT_JSON_PATH}...")
    with open(PROMPT_JSON_PATH, "r", encoding="utf-8") as f:
        prompt_templates = json.load(f)

    logger.info(f"📂 Loading scraped suggestions from {SCRAPED_SUCCESS_PATH}...")
    scraped_df = load_csv(SCRAPED_SUCCESS_PATH)
    scraped_df = scraped_df[scraped_df['suggestion'].notnull() & (scraped_df['suggestion'].str.strip() != '')]

    if scraped_df.empty:
        logger.warning("⚠️ No valid suggestions found. Exiting.")
        return

    blog_metadata_df = process_suggestions(scraped_df, prompt_templates)

    if not blog_metadata_df.empty:
        logger.info(f"💾 Saving blog metadata to {BLOG_METADATA_OUTPUT_PATH}...")
        save_csv(blog_metadata_df, BLOG_METADATA_OUTPUT_PATH)
        logger.info("🏁 Post-Processing Completed Successfully!")
    else:
        logger.warning("⚠️ No blog entries were successfully processed.")

if __name__ == "__main__":
    main()
