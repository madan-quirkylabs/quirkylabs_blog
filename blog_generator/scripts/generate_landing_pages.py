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
import requests

# Setup project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load internal modules
from utils.paths import INPUT_DIR, SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, SECTION_PROMPTS_PATH, RETRIES_DIR
from config.config_loader import load_config, load_pillar_config
from core.openai_client import OpenAIClient

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load config and OpenAI client
config = load_config()
pillar_config = load_pillar_config()
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

FAQ_TYPES = {
    "faq_google_autocomplete": {"style": "searchy"},
    "faq_core": {"style": "informational"},
    "faq_curious": {"style": "quirky"},
    "faq_cta": {"style": "cta"}
}

def interpolate_prompt(prompt, topic, primary_keyword):
    return (prompt.replace("{{Topic}}", topic)
                 .replace("{{topic}}", topic)
                 .replace("{{Primary Keyword}}", primary_keyword)
                 .replace("{{primary_keyword}}", primary_keyword))

def generate_faq_questions(section_key, topic, keyword):
    faq_def = next(item for item in faq_section_defs if item["key"] == section_key)
    prompt = interpolate_prompt(faq_def["prompt"], topic, keyword)
    system_instruction = faq_def["system_instruction"]

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]
    raw = openai_client.chat_completion(messages)

    raw_lines = raw.strip().split("\n")
    questions = [line.strip("-•* 1234567890.").strip() for line in raw_lines if "?" in line and len(line.strip()) > 5]
    return questions

def generate_answer_for_question(question):
    followup_prompt = f"Answer this question in 3–4 sentences using a helpful, cozy tone: \"{question}\""
    messages = [
        {"role": "system", "content": "You're a friendly ADHD coach writing validating answers for FAQs."},
        {"role": "user", "content": followup_prompt}
    ]
    return openai_client.chat_completion(messages)

def generate_faq_section(section_key, topic, keyword):
    questions = generate_faq_questions(section_key, topic, keyword)
    faq_blocks = []

    for question in questions:
        answer = generate_answer_for_question(question)
        faq_blocks.append(f"<details><summary>{question}</summary><p>{answer.strip()}</p></details>")

    return "\n".join(faq_blocks)

def generate_section(section, topic, primary_keyword):
    prompt = prompts_dict.get(section, {}).get("prompt")
    system_instruction = prompts_dict.get(section, {}).get("system_instruction")

    if not prompt or not system_instruction:
        raise KeyError(f"Prompt or system_instruction missing for section '{section}'")

    prompt = interpolate_prompt(prompt, topic, primary_keyword)

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    return openai_client.chat_completion(messages)

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
        clean_q = re.sub(r"<summary>|</summary>", "", q).strip()
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

def render_related_spokes(pillar_slug, current_slug):
    if pillar_slug not in pillar_config:
        return ""
    related_slugs = pillar_config[pillar_slug]["spokes"]
    links = []
    for slug in related_slugs:
        if slug == current_slug:
            continue
        title = slug.replace("-", " ").title()
        links.append(f"- [{title}](/pages/{slug}/)")
    if not links:
        return ""
    return "\n\n## Explore More in This Series\n\n" + "\n".join(links)

def build_front_matter(meta_title, meta_desc, slug, keywords):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    kws = "[" + ", ".join(f'\"{k.strip()}\"' for k in keywords.split(",") if k.strip()) + "]"
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

def assemble_blog(sections, row):
    all_faq_html = "".join([f"### {f['heading']}\n" + sections[f['key']] for f in faq_section_defs if f['key'] in sections])
    faq_structured = faq_to_jsonld(all_faq_html)
    related_block = render_related_spokes(row['pillar_slug'], row['slug'])

    return f"""
{sections['emotional_hook']}

{sections['story_part_1']}

{sections['story_part_2']}

{sections['story_part_3']}

## Quickfire ADHD Checklist

{sections['checklist']}

## Frequently Asked Questions

{all_faq_html}

<script type=\"application/ld+json\">
{faq_structured}
</script>
{related_block}"""

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

def generate_keywords_from_blog(topic, blog_body):
    prompt_template = prompts_dict["keyword_generation"]["prompt"]
    system_instruction = prompts_dict["keyword_generation"]["system_instruction"]

    prompt = prompt_template.replace("{{Topic}}", topic).replace("{{Content}}", blog_body[:1500])

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    try:
        response = openai_client.chat_completion(messages)
        return response
    except Exception as e:
        print(f"[KeywordGen] Error: {e}")
        return "ADHD, Neurodivergence"

def check_readability(text):
    return textstat.flesch_reading_ease(text), textstat.flesch_kincaid_grade(text)

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
                    if section in FAQ_TYPES:
                        content = generate_faq_section(section, topic, keyword)
                    else:
                        content = generate_section(section, topic, keyword)

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

        blog = assemble_blog(sections, row)
        generated_keywords = generate_keywords_from_blog(topic, blog)
        gpt_keywords = [kw.strip() for kw in generated_keywords.split(",") if kw.strip()]
        keywords = ",".join(gpt_keywords[:7])

        flesch, grade = check_readability(blog)
        log["readability"] = {"flesch": flesch, "grade": grade}

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
