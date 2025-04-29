import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import concurrent.futures
import logging
from utils.paths import INPUT_DIR, SUCCESS_DIR, FAILURE_DIR, LOGS_DIR
from config.config_loader import load_config
from core.openai_client import OpenAIClient
import pandas as pd

# Load configuration
config = load_config()
openai_client = OpenAIClient(config)

# Create output directories if they don't exist
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Load input CSV
input_file = os.path.join(INPUT_DIR, "sample_input.csv")
df = pd.read_csv(input_file)

# Utility function to generate a single blog
def generate_blog(row):
    blog_title = row["title"]
    topic = row["topic"]
    slug = row["slug"]

    try:
        logging.info(f"🚀 Starting blog generation for: {topic}")

        # 1. Build the prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant..."},
            {"role": "user", "content": f"Write a blog about {topic}"}
        ]

        # 2. Call OpenAI
        blog_content = openai_client.chat_completion(messages)

        # 3. Save the blog
        output_path = os.path.join(SUCCESS_DIR, f"{slug}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(blog_content)

        logging.info(f"✅ Blog generated: {output_path}")

        return {"slug": slug, "status": "success", "path": output_path}

    except Exception as e:
        logging.error(f"❌ Error generating blog for {topic}: {e}")
        failure_path = os.path.join(FAILURE_DIR, f"{slug}.txt")
        with open(failure_path, "w", encoding="utf-8") as f:
            f.write(str(e))

        return {"slug": slug, "status": "failure", "error": str(e)}

# Run generation in parallel
def main():
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=config["generation"]["parallel_threads"]) as executor:
        futures = [executor.submit(generate_blog, row) for _, row in df.iterrows()]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)

    # Save log summary
    log_summary_path = os.path.join(LOGS_DIR, "generation_summary.json")
    with open(log_summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"🏁 Finished generating {len(results)} blogs. Summary saved at {log_summary_path}")

if __name__ == "__main__":
    main()
