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

# Load config and OpenAI client
config = load_config()
openai_client = OpenAIClient(config)

# Ensure output dirs exist
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Load input CSV
df = pd.read_csv(os.path.join(INPUT_DIR, "sample_input.csv"))
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# Load prompts
with open(SECTION_PROMPTS_PATH, "r", encoding="utf-8") as f:
    prompts_dict = json.load(f)

# --- Section Helpers ---
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

def validate_faq(content, primary_keyword):
    soup = BeautifulSoup(content, "html.parser")
    questions = [summary.get_text().lower() for summary in soup.find_all("summary")]
    keyword_matches = sum(1 for q in questions if primary_keyword.lower() in q)
    return len(questions) >= 5 and keyword_matches >= 2

def generate_section(section, topic, primary_keyword):
    prompt = prompts_dict[section]["prompt"].replace("{{Topic}}", topic).replace("{{Primary Keyword}}", primary_keyword)
    system_instruction = prompts_dict[section]["system_instruction"]
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]
    return openai_client.chat_completion(messages)

def check_readability(text):
    return textstat.flesch_reading_ease(text), textstat.flesch_kincaid_grade(text)

def generate_meta_description(topic, keyword):
    prompt = f"Write a short, playful meta description under 155 characters for a blog about '{topic}' including the keyword '{keyword}'. Make it cozy and intriguing."
    instruction = "You are a playful SEO copywriter. Generate a short (max 155 characters) meta description for an ADHD-friendly blog."
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": prompt}
    ]
    return openai_client.chat_completion(messages)

def validate_blog(content, topic):
    structural_prompt = prompts_dict["validation"]["prompt"].replace("{{BlogContent}}", content)
    structural_instruction = prompts_dict["validation"]["system_instruction"]
    topic_prompt = prompts_dict["topic_relevance_validation"]["prompt"].replace("{{Topic}}", topic) + "\n\n" + content
    topic_instruction = prompts_dict["topic_relevance_validation"]["system_instruction"]
    structural_result = openai_client.chat_completion([
        {"role": "system", "content": structural_instruction},
        {"role": "user", "content": structural_prompt}
    ])
    topic_result = openai_client.chat_completion([
        {"role": "system", "content": topic_instruction},
        {"role": "user", "content": topic_prompt}
    ])
    return structural_result, topic_result

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

def assemble_blog(sections):
    faq_structured = faq_to_jsonld(sections["faq"])
    sections['faq'] += "\n\n" + sections['faq_cta']
    return f"""
{sections['emotional_hook']}

{sections['story_part_1']}

{sections['story_part_2']}

{sections['story_part_3']}

## Quickfire ADHD Checklist

{sections['checklist']}

## Frequently Asked Questions

{sections['faq']}

<script type=\"application/ld+json\">
{faq_structured}
</script>
"""

def save_log(slug, obj):
    with open(os.path.join(LOGS_DIR, f"{slug}.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def save_retry_payload(row, reason):
    payload = {
        "topic": row["topic"],
        "primary_keyword": row["primary_keyword"],
        "slug": row["slug"],
        "failure_reason": reason
    }
    with open(os.path.join(RETRIES_DIR, f"{row['slug']}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def generate_blog(row):
    topic = row["topic"]
    keyword = row["primary_keyword"]
    slug = row["slug"]
    meta_title = row.get("meta_title", topic)
    keywords = row.get("keywords", "")

    sections = {}
    log = {
        "slug": slug,
        "topic": topic,
        "start_time": datetime.utcnow().isoformat(),
        "section_attempts": [],
        "status": "in_progress"
    }

    section_order = ["emotional_hook", "story_part_1", "story_part_2", "story_part_3", "checklist", "faq", "faq_cta", "cta"]

    try:
        for section in section_order:
            success = False
            log["section_attempts"].append({"section": section, "attempts": []})

            for attempt in range(config["openai"]["max_retries"]):
                try:
                    print(f"🧠 Generating section: {section}, attempt {attempt + 1}")
                    content = generate_section(section, topic, keyword)

                    if section == "faq" and not validate_faq(content, keyword):
                        print(f"⚠️ Validation failed for FAQ section. Retrying...")
                        log["section_attempts"][-1]["attempts"].append({"status": "fail", "reason": "invalid_faq"})
                        continue

                    sections[section] = content
                    log["section_attempts"][-1]["attempts"].append({"status": "success"})
                    success = True
                    print(f"✅ Section {section} generated successfully.")
                    break

                except Exception as e:
                    log["section_attempts"][-1]["attempts"].append({"status": "fail", "error": str(e)})
                    print(f"❌ Error generating section {section}, attempt {attempt + 1}: {e}")

            if not success:
                if section == "faq_cta":
                    # Fail-safe fallback
                    fallback_cta = (
                        "<details>\n"
                        "<summary>How can I check if I might have ADHD?</summary>\n"
                        "<p>We created a playful self-assessment at "
                        "[QuirkyLabs.ai](https://quirkylabs.ai) to help you reflect. "
                        "It’s not a diagnosis—just a cozy nudge toward better understanding.</p>\n"
                        "</details>"
                    )
                    sections["faq_cta"] = fallback_cta
                    log["section_attempts"][-1]["fallback_used"] = True
                    print("⚙️ Using fallback for faq_cta.")
                    continue

                # For all other sections, fail if none succeeded
                log["status"] = "failed_section"
                save_log(slug, log)
                save_retry_payload(row, section)
                return

        blog = assemble_blog(sections)
        flesch, grade = check_readability(blog)
        log["readability"] = {"flesch": flesch, "grade": grade}

        if config["generation"]["validate_readability"] and (flesch < 50 or grade > 8):
            log["status"] = "failed_readability"
            save_log(slug, log)
            save_retry_payload(row, "readability_failure")
            return

        s_report, t_report = validate_blog(blog, topic)
        log["qa_reports"] = {"structural": s_report, "topic": t_report}

        if "fail" in s_report.lower() or "fail" in t_report.lower():
            log["status"] = "failed_qa"
            save_log(slug, log)
            save_retry_payload(row, "qa_failure")
            return

        meta_desc = generate_meta_description(topic, keyword)
        log["meta_description"] = meta_desc
        front = build_front_matter(meta_title, meta_desc, slug, keywords)

        with open(os.path.join(SUCCESS_DIR, f"{slug}.md"), "w", encoding="utf-8") as f:
            f.write(front + blog.strip())

        log["status"] = "success"
        save_log(slug, log)

    except Exception as e:
        log["status"] = "fatal_error"
        log["error"] = str(e)
        save_log(slug, log)
        save_retry_payload(row, "fatal_error")

def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=config["generation"]["parallel_threads"]) as executor:
        futures = [executor.submit(generate_blog, row) for _, row in df.iterrows()]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    print(f"✅ Finished generating blogs. See logs in: {LOGS_DIR}")

if __name__ == "__main__":
    main()
