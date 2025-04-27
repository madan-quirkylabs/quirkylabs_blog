# retry_failed_blogs.py

import csv
import os
from parallel_generate_landing_pages import process_blog, load_json, create_output_dirs

# --- CONFIGURATION ---
FAILED_LOG = "output/failed_blogs.csv"
PROMPTS_FILE = "quirkylabs_section_prompts.json"
OUTPUT_DIR = "output/landing_pages/"
SAFE_SLEEP_SECONDS = 1.5

def load_failed_blogs():
    if not os.path.exists(FAILED_LOG):
        print("❌ No failed_blogs.csv found. Nothing to retry.")
        return []
    
    with open(FAILED_LOG, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def retry_failed():
    create_output_dirs()
    prompts_dict = load_json(PROMPTS_FILE)
    failed_blogs = load_failed_blogs()

    if not failed_blogs:
        print("✅ No failed blogs to retry.")
        return

    for row in failed_blogs:
        print(f"🔄 Retrying blog: {row['Topic']}")
        minimal_row = {
            "Topic": row['Topic'],
            "Slug": row['Slug'],
            "Primary Keyword": row['Topic'],  # fallback if keyword missing
            "Meta Title": row['Topic'],
            "Meta Description": f"Learn more about {row['Topic']} with QuirkyLabs!",
            "Keywords": row['Topic']
        }
        process_blog(minimal_row, prompts_dict)

    print("✅ Retry process completed.")

if __name__ == "__main__":
    retry_failed()
