import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import concurrent.futures
import logging
from utils.paths import RETRIES_DIR, SUCCESS_DIR, FAILURE_DIR, LOGS_DIR
from config.config_loader import load_config
from core.openai_client import OpenAIClient

# Load configuration
config = load_config()
openai_client = OpenAIClient(config)

# Create output directories if they don't exist
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Load retry tasks
retry_files = [f for f in os.listdir(RETRIES_DIR) if f.endswith(".json")]

def retry_blog(file_name):
    slug = file_name.replace(".json", "")

    try:
        logging.info(f"🔁 Retrying blog for: {slug}")

        with open(os.path.join(RETRIES_DIR, file_name), "r", encoding="utf-8") as f:
            retry_payload = json.load(f)

        messages = retry_payload["messages"]

        # Retry with OpenAI
        blog_content = openai_client.chat_completion(messages)

        # Save success
        output_path = os.path.join(SUCCESS_DIR, f"{slug}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(blog_content)

        logging.info(f"✅ Retry successful: {output_path}")

        return {"slug": slug, "status": "success", "path": output_path}

    except Exception as e:
        logging.error(f"❌ Retry failed for {slug}: {e}")
        failure_path = os.path.join(FAILURE_DIR, f"{slug}.txt")
        with open(failure_path, "w", encoding="utf-8") as f:
            f.write(str(e))

        return {"slug": slug, "status": "failure", "error": str(e)}

# Run retries in parallel
def main():
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=config["generation"]["parallel_threads"]) as executor:
        futures = [executor.submit(retry_blog, file_name) for file_name in retry_files]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

    # Save retry summary
    log_summary_path = os.path.join(LOGS_DIR, "retry_summary.json")
    with open(log_summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"🏁 Finished retrying {len(results)} blogs. Summary saved at {log_summary_path}")

if __name__ == "__main__":
    main()
