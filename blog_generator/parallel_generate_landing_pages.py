# 🚀 Full parallel_generate_landing_pages.py (with Micro-Validations, Model Routing, Rate Limit Handling, and Tuned Story Part Injection)

import csv
import os
import time
import random
import json
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import textstat
import re

# --- CONFIGURATION ---
MODEL_GENERATION = "gpt-4"
MODEL_VALIDATION = "gpt-4o"
TEST_MODE = True
STRICT_MODE = True
INPUT_CSV = "sample_input.csv"
OUTPUT_DIR = "output/landing_pages/"
FAILED_LOG = "output/failed_blogs.csv"
PASSED_LOG = "output/passed_blogs.csv"
PROMPTS_FILE = "quirkylabs_section_prompts.json"
MAX_RETRIES = 3
MAX_BLOGS_IN_PARALLEL = 3
SAFE_SLEEP_SECONDS = 1.5

# --- External ADHD Resources ---
EXTERNAL_LINKS = [
    ("Learn more at CHADD", "https://chadd.org"),
    ("See CDC's ADHD overview", "https://www.cdc.gov/ncbddd/adhd/index.html"),
    ("Read more on ADDitudeMag", "https://www.additudemag.com"),
    ("Explore ADHD tips on Understood.org", "https://www.understood.org"),
    ("Visit ADHD Foundation", "https://www.adhdfoundation.org.uk"),
    ("Medical overview at Mayo Clinic", "https://www.mayoclinic.org/diseases-conditions/adhd/symptoms-causes/syc-20350889"),
    ("See ADHD research at NIH", "https://www.nimh.nih.gov/health/topics/attention-deficit-hyperactivity-disorder-adhd")
]

# --- Initialize OpenAI Client ---
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# --- Helper Functions ---

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_output_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(FAILED_LOG), exist_ok=True)
    os.makedirs(os.path.dirname(PASSED_LOG), exist_ok=True)

def log_failed_blog(row, reason):
    header = not os.path.exists(FAILED_LOG)
    with open(FAILED_LOG, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Topic', 'Slug', 'Reason']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if header:
            writer.writeheader()
        writer.writerow({'Topic': row['Topic'], 'Slug': row['Slug'], 'Reason': reason})

def log_passed_blog(row):
    header = not os.path.exists(PASSED_LOG)
    with open(PASSED_LOG, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Topic', 'Slug']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if header:
            writer.writeheader()
        writer.writerow({'Topic': row['Topic'], 'Slug': row['Slug']})

def model_router(task_type):
    if task_type == "generation":
        return MODEL_GENERATION
    elif task_type == "validation":
        return MODEL_VALIDATION
    else:
        return MODEL_GENERATION

def call_openai(prompt, system_instruction, task_type="generation"):
    model = model_router(task_type)
    time.sleep(SAFE_SLEEP_SECONDS)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            )
            result = response.choices[0].message.content.strip()
            if result:
                return result
        except Exception as e:
            error_msg = str(e)
            if 'rate limit' in error_msg.lower():
                wait_match = re.search(r"Please try again in (\d+\.?\d*)s", error_msg)
                if wait_match:
                    wait_seconds = float(wait_match.group(1)) + 2.0
                else:
                    wait_seconds = 20.0
                print(f"Rate limit hit. Sleeping for {wait_seconds:.2f} seconds...")
                time.sleep(wait_seconds)
            else:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(f"Attempt {attempt+1} failed during OpenAI call: {e}. Retrying in {wait_time:.2f} seconds.")
                time.sleep(wait_time)
    return None

def readability_check(blog_content):
    flesch_score = textstat.flesch_reading_ease(blog_content)
    grade_level = textstat.flesch_kincaid_grade(blog_content)
    print(f"\n🧠 Readability Scores:\n- Flesch Reading Ease: {flesch_score:.2f}\n- Flesch-Kincaid Grade Level: {grade_level:.2f}")
    return flesch_score, grade_level

def build_front_matter(meta_title, meta_description, slug, keywords):
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    keywords_list = [k.strip() for k in keywords.split(",")]
    keywords_yaml = '[' + ', '.join(f'"{kw}"' for kw in keywords_list) + ']'
    return f"""---
title: \"{meta_title}\"
description: \"{meta_description}\"
slug: \"{slug}\"
date: {today_date}
draft: false
type: \"page\"
categories: [\"ADHD Guides\"]
tags: [\"ADHD\", \"Neurodivergence\"]
keywords: {keywords_yaml}
---\n\n"""

def assemble_blog(sections):
    anchor_text, url = random.choice(EXTERNAL_LINKS)
    external_link_line = f"\n> 🔗 {anchor_text}: [{url}]({url})\n"
    return f"""
{sections['emotional_hook']}

{sections['story_part_1']}

{sections['story_part_2']}

{sections['story_part_3']}

## ✅ Quickfire ADHD Checklist

{sections['checklist']}
{external_link_line}

## ❓ Frequently Asked Questions

{sections['faq']}

{sections['cta']}
"""

def micro_validate_blog(blog_content, topic, primary_keyword, validations_dict):
    total_checks = len(validations_dict)
    passes = 0
    failures = []

    for validation_name, validation in validations_dict.items():
        prompt = validation['prompt'].replace("{{Topic}}", topic).replace("{{Primary Keyword}}", primary_keyword)
        system_instruction = validation['system_instruction']

        result = call_openai(prompt + "\n\n" + blog_content, system_instruction, task_type="validation")

        if not result:
            print(f"❌ Validation '{validation_name}' returned empty. Counting as failure.")
            failures.append(validation_name)
            continue

        if '✅' in result:
            passes += 1
            print(f"✅ Validation passed: {validation_name}")
        else:
            print(f"❌ Validation failed: {validation_name}")
            failures.append(validation_name)

    threshold = total_checks - 1

    if passes >= threshold:
        return True, failures
    else:
        return False, failures

def process_blog(row, prompts_dict):
    print(f"\n🚀 Starting blog generation for: {row['Topic']}")

    sections = {}
    section_order = ['emotional_hook', 'story_part_1', 'story_part_2', 'story_part_3', 'checklist', 'faq', 'cta']

    for idx, part in enumerate(section_order):
        section = prompts_dict[part]
        prompt = section['prompt'].replace("{{Topic}}", row['Topic']).replace("{{Primary Keyword}}", row['Primary Keyword'])

        if 'Part {{N}}' in prompt:
            prompt = prompt.replace("Part {{N}}", f"Part {idx}")

        system_instruction = section['system_instruction']
        result = call_openai(prompt, system_instruction, task_type="generation")

        if not result:
            print(f"❌ Section generation failed: {part}")
            log_failed_blog(row, f"Section failure: {part}")
            return

        sections[part] = result

    blog_content = assemble_blog(sections)

    flesch_score, grade_level = readability_check(blog_content)
    if STRICT_MODE and flesch_score < 65:
        print(f"⚠️ Readability warning: Score {flesch_score:.2f}. Blog flagged.")

    if STRICT_MODE:
        passed, failed_validations = micro_validate_blog(blog_content, row['Topic'], row['Primary Keyword'], prompts_dict['micro_validations'])

        if not passed:
            print(f"❌ Blog failed validations: {failed_validations}")
            log_failed_blog(row, f"Micro Validation Failure: {failed_validations}")
            return

    generated_meta_description = generate_meta_description(row['Topic'], row['Primary Keyword'])
    front_matter = build_front_matter(row['Meta Title'], generated_meta_description, row['Slug'], row['Keywords'])

    filepath = os.path.join(OUTPUT_DIR, f"{row['Slug']}.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter)
        f.write(blog_content.strip())

    print(f"✅ Blog saved successfully: {filepath}")
    log_passed_blog(row)

def generate_meta_description(topic, primary_keyword):
    prompt = (
        f"Write an SEO-optimized meta description (under 155 characters) "
        f"for a blog post about '{topic}' including '{primary_keyword}'."
    )
    system_instruction = (
        "Generate a vivid, ADHD-friendly, SEO-optimized meta description under 155 characters. "
        "Focus on clarity and keyword relevance first, coziness second."
    )
    return call_openai(prompt, system_instruction, task_type="generation")

def main():
    create_output_dirs()
    prompts_dict = load_json(PROMPTS_FILE)

    with open(INPUT_CSV, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    if TEST_MODE:
        rows = rows[:3]

    with ThreadPoolExecutor(max_workers=MAX_BLOGS_IN_PARALLEL) as executor:
        futures = [executor.submit(process_blog, row, prompts_dict) for row in rows]
        for _ in as_completed(futures):
            pass

if __name__ == "__main__":
    main()
