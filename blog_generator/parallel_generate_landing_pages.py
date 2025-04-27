# 🚀 Full Future-Proofed parallel_generate_landing_pages.py (with Dynamic Meta, SEO, External Links, and Everything!)

import csv
import os
import time
import random
import json
import re
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import textstat

# --- CONFIGURATION ---
MODEL = "gpt-4"
TEST_MODE = True
INPUT_CSV = "sample_input.csv"
OUTPUT_DIR = "output/landing_pages/"
FAILED_LOG = "output/failed_blogs.csv"
PASSED_LOG = "output/passed_blogs.csv"
PROMPTS_FILE = "quirkylabs_section_prompts.json"
MAX_RETRIES = 2
MAX_BLOGS_IN_PARALLEL = 3
MAX_SECTIONS_IN_PARALLEL = 5
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

def call_openai(prompt, system_instruction):
    time.sleep(SAFE_SLEEP_SECONDS)
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            wait_time = 2 ** attempt + random.uniform(0, 1)
            print(f"Attempt {attempt+1} failed during OpenAI call: {e}. Retrying in {wait_time:.2f} seconds.")
            time.sleep(wait_time)
    return None

def validate_faq_content(faq_content):
    return faq_content.count("<summary>") >= 5

def generate_section(section_name, topic, primary_keyword, prompts_dict):
    print(f"\n🛠 Generating section: {section_name}")
    section = prompts_dict[section_name]
    prompt = section['prompt'].replace("{{Topic}}", topic).replace("{{Primary Keyword}}", primary_keyword)
    system_instruction = section['system_instruction']
    return call_openai(prompt, system_instruction)

def safe_generate_section(section_name, topic, primary_keyword, prompts_dict, validate_func=None):
    for attempt in range(MAX_RETRIES + 1):
        result = generate_section(section_name, topic, primary_keyword, prompts_dict)
        if not result:
            print(f"⚠️ Empty output for section {section_name}. Retrying attempt {attempt+1}...")
            continue
        if validate_func and not validate_func(result):
            print(f"⚠️ Validation failed for {section_name}. Retrying attempt {attempt+1}...")
            continue
        print(f"✅ Section {section_name} generated successfully.")
        return result
    print(f"❌ Section {section_name} failed after retries.")
    return None

def quality_check(blog_content, prompts_dict, topic):
    if not blog_content.strip():
        return "fail - empty content", "fail - empty content"
    structural_prompt = prompts_dict['validation']['prompt'].replace("{{BlogContent}}", blog_content)
    structural_instruction = prompts_dict['validation']['system_instruction']
    topic_prompt = prompts_dict['topic_relevance_validation']['prompt'].replace("{{Topic}}", topic)
    topic_instruction = prompts_dict['topic_relevance_validation']['system_instruction']
    time.sleep(SAFE_SLEEP_SECONDS)
    structural_report = call_openai(structural_prompt, structural_instruction)
    topic_report = call_openai(topic_prompt + "\n\n" + blog_content, topic_instruction)
    return structural_report, topic_report

def generate_meta_description(topic, primary_keyword):
    prompt = (
        f"Write an SEO-optimized meta description (under 155 characters) "
        f"for a blog post about '{topic}'. It should clearly state what the post covers, "
        f"include the keyword '{primary_keyword}' naturally, and feel cozy but clear."
    )
    system_instruction = (
        "Generate a vivid, ADHD-friendly, SEO-optimized meta description under 155 characters. "
        "Focus on clarity and keyword relevance first, coziness second. "
        "Meta description must be clear enough to improve Google click-through rates (CTR)."
    )
    return call_openai(prompt, system_instruction)

def assemble_blog(sections):
    # Pick a random external link
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

def readability_check(blog_content):
    flesch_score = textstat.flesch_reading_ease(blog_content)
    grade_level = textstat.flesch_kincaid_grade(blog_content)
    print(f"\n🧠 Readability Scores:")
    print(f"- Flesch Reading Ease: {flesch_score:.2f}")
    print(f"- Flesch-Kincaid Grade Level: {grade_level:.2f}")
    return flesch_score, grade_level

def process_blog(row, prompts_dict):
    print(f"\n🚀 Starting blog generation for: {row['Topic']}")

    sections = {}
    parts = ['emotional_hook', 'story_part_1', 'story_part_2', 'story_part_3', 'checklist', 'faq', 'cta']
    validations = { 'faq': validate_faq_content }

    for part in parts:
        validate_func = validations.get(part)
        result = safe_generate_section(part, row['Topic'], row['Primary Keyword'], prompts_dict, validate_func)
        if not result:
            print(f"❌ Skipping blog {row['Slug']} due to failure in section: {part}")
            log_failed_blog(row, f"Section failure: {part}")
            return
        sections[part] = result

    blog_content = assemble_blog(sections)
    flesch_score, grade_level = readability_check(blog_content)

    if flesch_score < 65:
        print(f"⚠️ Readability warning: Score {flesch_score:.2f}. Consider reviewing.")

    structural_report, topic_report = quality_check(blog_content, prompts_dict, row['Topic'])
    print(f"\n🔎 Structural QA Report:\n{structural_report}")
    print(f"\n🔎 Topic QA Report:\n{topic_report}")

    if ("fail" in structural_report.lower() or "fail" in topic_report.lower()) or ("missing" in structural_report.lower() or "missing" in topic_report.lower()):
        print(f"❌ Blog failed QA checks: {row['Slug']}")
        log_failed_blog(row, "QA Failure")
        return

    generated_meta_description = generate_meta_description(row['Topic'], row['Primary Keyword'])

    front_matter = build_front_matter(row['Meta Title'], generated_meta_description, row['Slug'], row['Keywords'])
    filepath = os.path.join(OUTPUT_DIR, f"{row['Slug']}.md")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter)
        f.write(blog_content.strip())

    print(f"✅ Blog saved successfully: {filepath}")
    log_passed_blog(row)

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
