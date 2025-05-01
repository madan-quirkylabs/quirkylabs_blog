# 📄 Updated retry_failed_blogs.py - Step 4 Refactor: Move retry_blog to core/retry_service.py

import os
import sys
import json
import concurrent.futures
import logging
import pandas as pd
from datetime import datetime

# Setup project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load internal modules
from utils.paths import RETRIES_DIR, SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, PERMANENT_FAILURE_DIR
from utils.colors import bcolors
from utils.file_ops import delete_file, move_file
from config.config_loader import load_config
from core.retry_service import retry_blog  # 🆕 moved logic

# --- Load configuration ---
config = load_config()

# Create output directories if not exist
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Load retry files
def load_retry_files():
    return [f for f in os.listdir(RETRIES_DIR) if f.endswith(".json")]

# Save CSV summaries
def save_summary_csv(results):
    success_rows = [r for r in results if r and r.get("status") == "success"]
    failed_rows = [r for r in results if not r or r.get("status") != "success"]

    if success_rows:
        success_df = pd.DataFrame(success_rows)
        success_csv_path = os.path.join(LOGS_DIR, "passed_blogs.csv")
        success_df.to_csv(success_csv_path, index=False)
        print(f"{bcolors.OKGREEN}✅ Passed blogs saved to {success_csv_path}{bcolors.ENDC}")

    if failed_rows:
        failed_df = pd.DataFrame(failed_rows)
        failed_csv_path = os.path.join(LOGS_DIR, "failed_blogs.csv")
        failed_df.to_csv(failed_csv_path, index=False)
        print(f"{bcolors.FAIL}❌ Failed blogs saved to {failed_csv_path}{bcolors.ENDC}")

# Main retry runner
def main():
    results = []

    retry_files = load_retry_files()
    if not retry_files:
        print(f"{bcolors.OKGREEN}✅ No blogs to retry.{bcolors.ENDC}")
        return

    print(f"{bcolors.HEADER}🔄 Retrying {len(retry_files)} blogs...{bcolors.ENDC}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=config["generation"]["parallel_threads"]) as executor:
        futures = [executor.submit(retry_blog, file_name) for file_name in retry_files]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')
    retry_summary_path = os.path.join(LOGS_DIR, f"retry_summary_{timestamp}.json")
    with open(retry_summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"{bcolors.OKGREEN}🏁 Retry process completed. Summary saved at {retry_summary_path}{bcolors.ENDC}")

    save_summary_csv(results)

if __name__ == "__main__":
    main()
