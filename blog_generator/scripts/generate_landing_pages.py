import os
import sys
import json
import concurrent.futures
import logging
import pandas as pd
import textstat
from datetime import datetime
import re
from bs4 import BeautifulSoup

# Setup project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load internal modules
from utils.paths import INPUT_DIR, SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, SECTION_PROMPTS_PATH, RETRIES_DIR
from config.config_loader import load_config
from core.openai_client import OpenAIClient

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load config and OpenAI client
config = load_config()
openai_client = OpenAIClient(config)

# Ensure output dirs exist
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, RETRIES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Load input CSV
input_path = os.path.join(INPUT_DIR, "sample_input.csv")
df = pd.read_csv(input_path)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# Load prompts
with open(SECTION_PROMPTS_PATH, "r", encoding="utf-8") as f:
    prompts_dict = json.load(f)

faq_section_defs = prompts_dict.get("faq_sections", [])
faq_section_keys = [fs["key"] for fs in faq_section_defs]

section_order = [
    "emotional_hook",
    "story_part_1",
    "story_part_2",
    "story_part_3",
    "checklist",
    *faq_section_keys,
    "cta"
]

def interpolate_prompt(prompt, topic, primary_keyword):
    return (prompt.replace("{{Topic}}", topic)
                 .replace("{{topic}}", topic)
                 .replace("{{Primary Keyword}}", primary_keyword)
                 .replace("{{primary_keyword}}", primary_keyword))

def faq_to_jsonld(faq_html):
    pattern = re.compile(r"<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>", re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(faq_html)

    def strip_html_tags(html):
        return BeautifulSoup(html, "html.parser").get_text().strip()

    jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": []
    }

    for q, a in matches:
        clean_q = re.sub(r"\s+", " ", q.strip())
        clean_a = strip_html_tags(a)
        jsonld["mainEntity"].append({
            "@type": "Question",
            "name": clean_q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": clean_a
            }
        })

    return json.dumps(jsonld, indent=2)

def normalize(text):
    return re.sub(r'\W+', ' ', text.lower()).strip()

def validate_faq(content, primary_keyword, section_key):
    soup = BeautifulSoup(content, "html.parser")
    questions = [normalize(summary.get_text()) for summary in soup.find_all("summary")]
    keyword_normalized = normalize(primary_keyword)
    keyword_matches = sum(1 for q in questions if keyword_normalized in q)

    if section_key == "faq_cta":
        if len(questions) != 1 or keyword_matches < 1:
            logging.warning(f"⚠️ FAQ CTA validation failed. Found {len(questions)} questions, {keyword_matches} keyword matches.")
            logging.debug("FAQ content:\n" + content)
            return False
    else:
        if len(questions) < 4 or keyword_matches < 1:
            logging.warning(f"⚠️ FAQ validation failed. Found {len(questions)} questions, {keyword_matches} keyword matches.")
            logging.debug("FAQ content:\n" + content)
            return False

    return True

def generate_section(section, topic, primary_keyword, custom_prompt=None, custom_system=None):
    logging.debug(f"Preparing to generate section: {section}")

    prompt = custom_prompt or prompts_dict.get(section, {}).get("prompt")
    system_instruction = custom_system or prompts_dict.get(section, {}).get("system_instruction")

    if not prompt or not system_instruction:
        raise KeyError(f"Prompt or system_instruction missing for section '{section}'")

    prompt = prompt.replace("{{Topic}}", topic)
    
    prompt = prompt.replace("{{Primary Keyword}}", primary_keyword)
    prompt = prompt.replace("{{primary_keyword}}", primary_keyword)

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]
    return openai_client.chat_completion(messages)

def check_readability(text):
    return textstat.flesch_reading_ease(text), textstat.flesch_kincaid_grade(text)

def build_front_matter(meta_title, meta_desc, slug, keywords):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    kws = "[" + ", ".join(f'\"{k.strip()}\"' for k in keywords.split(",")) + "]"
    return f"""---
title: \"{meta_title}\"
description: \"{meta_desc}\"
slug: \"{slug}\"
date: {today}
draft: false
type: \"page\"
categories: [\"ADHD Guides\"]
tags: [\"ADHD\", \"Neurodivergence\"]
keywords: {kws}
---\n\n"""

def assemble_blog(sections, faq_section_defs):
    # Merge all FAQ HTML blocks without headings
    faq_section_keys = [f["key"] for f in faq_section_defs]
    all_faq_html = "\n".join([sections[key] for key in faq_section_keys if key in sections])

    # Generate FAQ structured data
    faq_structured = faq_to_jsonld(all_faq_html)

    return f"""
{sections['emotional_hook']}

{sections['story_part_1']}

{sections['story_part_2']}

{sections['story_part_3']}

## Quickfire ADHD Checklist

{sections['checklist']}

## Frequently Asked Questions

{all_faq_html}

<script type="application/ld+json">
{faq_structured}
</script>
"""

def save_log(slug, obj):
    path = os.path.join(LOGS_DIR, f"{slug}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def save_retry_payload(row, reason):
    payload = {
        "topic": row["topic"],
        "primary_keyword": row["primary_keyword"],
        "slug": row["slug"],
        "failure_reason": reason
    }
    retry_path = os.path.join(RETRIES_DIR, f"{row['slug']}.json")
    with open(retry_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def generate_blog(row):
    topic = row["topic"]
    keyword = row["primary_keyword"]
    slug = row["slug"]
    meta_title = row.get("meta_title", topic)
    keywords = row.get("keywords", "")

    sections = {}
    log = {"slug": slug, "topic": topic, "status": "in_progress", "section_attempts": []}

    try:
        for section in section_order:
            success = False
            log["section_attempts"].append({"section": section, "attempts": []})

            for attempt in range(config["openai"]["max_retries"]):
                try:
                    if section in faq_section_keys:
                        faq_def = next(item for item in faq_section_defs if item["key"] == section)
                        content = generate_section(section, topic, keyword, custom_prompt=faq_def["prompt"], custom_system=faq_def["system_instruction"])
                    else:
                        content = generate_section(section, topic, keyword)

                    if section.startswith("faq") and not validate_faq(content, keyword, section):
                        log["section_attempts"][-1]["attempts"].append({"status": "fail", "reason": "invalid_faq"})
                        continue

                    sections[section] = content
                    log["section_attempts"][-1]["attempts"].append({"status": "success"})
                    success = True
                    break

                except Exception as e:
                    log["section_attempts"][-1]["attempts"].append({"status": "fail", "error": str(e)})

            if not success:
                log["status"] = "failed_section"
                save_log(slug, log)
                save_retry_payload(row, section)
                return

        blog = assemble_blog(sections, faq_section_defs)
        flesch, grade = check_readability(blog)
        log["readability"] = {"flesch": flesch, "grade": grade}

        if config["generation"]["validate_readability"] and (flesch < 50 or grade > 8):
            log["status"] = "failed_readability"
            save_log(slug, log)
            save_retry_payload(row, "readability_failure")
            return

        meta_desc = f"Learn about {topic} and how it impacts ADHD minds."
        log["meta_description"] = meta_desc
        front = build_front_matter(meta_title, meta_desc, slug, keywords)

        output_path = os.path.join(SUCCESS_DIR, f"{slug}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(front + blog.strip())

        log["status"] = "success"
        save_log(slug, log)

    except Exception as e:
        log["status"] = "fatal_error"
        log["error"] = str(e)
        save_log(slug, log)
        save_retry_payload(row, "fatal_error")

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=config["generation"]["parallel_threads"]) as executor:
        futures = [executor.submit(generate_blog, row) for _, row in df.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()
