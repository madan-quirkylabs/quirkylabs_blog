# 🚀 Updated retry_failed_blogs.py (Strict Mode Compatible)

import csv
import os
from parallel_generate_landing_pages import process_blog, load_json, create_output_dirs, PROMPTS_FILE
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
FAILED_LOG = "output/failed_blogs.csv"
RETRY_FAILED_LOG = "output/retried_failed_blogs.csv"
MAX_BLOGS_IN_PARALLEL = 3

# --- Updated Helper Function ---
def load_failed_blogs():
    if not os.path.exists(FAILED_LOG):
        print("No failed blogs found to retry.")
        return []
    with open(FAILED_LOG, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)

def log_retry_failed_blog(row, reason):
    header = not os.path.exists(RETRY_FAILED_LOG)
    with open(RETRY_FAILED_LOG, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Topic', 'Slug', 'Reason']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if header:
            writer.writeheader()
        writer.writerow({'Topic': row['Topic'], 'Slug': row['Slug'], 'Reason': reason})

# --- Main Retry Logic ---
def retry_failed_blogs():
    create_output_dirs()
    prompts_dict = load_json(PROMPTS_FILE)
    failed_rows = load_failed_blogs()

    if not failed_rows:
        print("✅ No failed blogs to retry.")
        return

    print(f"\n🔄 Retrying {len(failed_rows)} failed blogs...")

    with ThreadPoolExecutor(max_workers=MAX_BLOGS_IN_PARALLEL) as executor:
        futures = []
        for row in failed_rows:
            futures.append(executor.submit(process_blog, row, prompts_dict))
        for _ in as_completed(futures):
            pass

    print("\n🎯 Retry process completed.")

if __name__ == "__main__":
    retry_failed_blogs()
