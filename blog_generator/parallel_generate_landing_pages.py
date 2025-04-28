# 🚀 FINAL - Corrected QA Validation - QuirkyLabs Blog Generator

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
LOGS_DIR = "output/logs/"
MAX_RETRIES = 2
MAX_BLOGS_IN_PARALLEL = 2
SAFE_SLEEP_SECONDS = 1.5
VERBOSE_LOGGING = True

# --- Initialize OpenAI Client ---
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# --- Helper Functions ---
def verbose_print(msg):
    if VERBOSE_LOGGING:
        print(msg)

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_output_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(FAILED_LOG), exist_ok=True)
    os.makedirs(os.path.dirname(PASSED_LOG), exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

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

def save_json_log(slug, log_obj):
    filepath = os.path.join(LOGS_DIR, f"{slug}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(log_obj, f, indent=2, ensure_ascii=False)

def call_openai(prompt, system_instruction, blog_log, section_name):
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
            result = response.choices[0].message.content.strip()
            blog_log['openai_calls'].append({
                "section": section_name,
                "attempt": attempt+1,
                "status": "success",
                "output_sample": result[:500]
            })
            return result
        except Exception as e:
            wait_time = 2 ** attempt + random.uniform(0, 1)
            blog_log['openai_calls'].append({
                "section": section_name,
                "attempt": attempt+1,
                "status": "fail",
                "error": str(e)
            })
            verbose_print(f"Attempt {attempt+1} failed during OpenAI call for {section_name}: {e}. Retrying in {wait_time:.2f} seconds.")
            time.sleep(wait_time)
    return None

def validate_faq_content(faq_content):
    return faq_content.count("<summary>") >= 5

def generate_meta_description(topic, primary_keyword, blog_log):
    prompt = f"Write a short, playful meta description under 155 characters for a blog about '{topic}'. Include the keyword '{primary_keyword}' naturally. Make it feel cozy and intriguing."
    system_instruction = "Generate an SEO meta description under 155 characters with playful, ADHD-friendly tone. Include keyword naturally."
    return call_openai(prompt, system_instruction, blog_log, "meta_description")

def generate_section(section_name, topic, primary_keyword, prompts_dict, blog_log):
    try:
        verbose_print(f"\n🛠 Generating section: {section_name}")
        section = prompts_dict[section_name]
        prompt = section['prompt'].replace("{{Topic}}", topic).replace("{{Primary Keyword}}", primary_keyword)
        system_instruction = section['system_instruction']
        return call_openai(prompt, system_instruction, blog_log, section_name)
    except Exception as e:
        verbose_print(f"❌ Error during section {section_name}: {e}")
        return None

def safe_generate_section(section_name, topic, primary_keyword, prompts_dict, blog_log, validate_func=None):
    for attempt in range(MAX_RETRIES + 1):
        result = generate_section(section_name, topic, primary_keyword, prompts_dict, blog_log)
        if not result:
            blog_log['section_failures'].append({"section": section_name, "reason": "empty_output", "attempt": attempt+1})
            continue
        if validate_func and not validate_func(result):
            blog_log['section_failures'].append({"section": section_name, "reason": "validation_failed", "attempt": attempt+1})
            continue
        blog_log['section_successes'].append({"section": section_name, "attempt": attempt+1})
        verbose_print(f"✅ Section {section_name} generated successfully.")
        return result
    verbose_print(f"❌ Section {section_name} failed after retries.")
    return None

def assemble_blog(sections):
    return f"""
{sections['emotional_hook']}

{sections['story_part_1']}

{sections['story_part_2']}

{sections['story_part_3']}

## ✅ Quickfire ADHD Checklist

{sections['checklist']}

## ❓ Frequently Asked Questions

{sections['faq']}

{sections['cta']}
"""

def quality_check(full_blog_content, prompts_dict, topic, blog_log):
    try:
        if not full_blog_content.strip():
            return "fail - empty content", "fail - empty content"
        structural_prompt = prompts_dict['validation']['prompt'].replace("{{BlogContent}}", full_blog_content)
        structural_instruction = prompts_dict['validation']['system_instruction']
        topic_prompt = prompts_dict['topic_relevance_validation']['prompt'].replace("{{Topic}}", topic)
        topic_instruction = prompts_dict['topic_relevance_validation']['system_instruction']
        time.sleep(SAFE_SLEEP_SECONDS)
        structural_report = call_openai(structural_prompt, structural_instruction, blog_log, "QA_structural")
        topic_report = call_openai(topic_prompt + "\n\n" + full_blog_content, topic_instruction, blog_log, "QA_topic")
        return structural_report, topic_report
    except Exception as e:
        verbose_print(f"⚠️ QA check failed: {e}")
        blog_log['qa_error'] = str(e)
        return "fail - qa error", "fail - qa error"

def readability_check(blog_content):
    flesch_score = textstat.flesch_reading_ease(blog_content)
    grade_level = textstat.flesch_kincaid_grade(blog_content)
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

def process_blog(row, prompts_dict):
    try:
        verbose_print(f"\n🚀 Starting blog generation for: {row['Topic']}")
        blog_log = {
            "topic": row['Topic'],
            "slug": row['Slug'],
            "start_time": datetime.now(timezone.utc).isoformat(),
            "section_successes": [],
            "section_failures": [],
            "openai_calls": []
        }

        sections = {}
        parts = ['emotional_hook', 'story_part_1', 'story_part_2', 'story_part_3', 'checklist', 'faq', 'cta']
        validations = {'faq': validate_faq_content}

        for part in parts:
            validate_func = validations.get(part)
            result = safe_generate_section(part, row['Topic'], row['Primary Keyword'], prompts_dict, blog_log, validate_func)
            if not result:
                blog_log['status'] = "failed"
                save_json_log(row['Slug'], blog_log)
                log_failed_blog(row, f"Section failure: {part}")
                return
            sections[part] = result

        blog_content = assemble_blog(sections)
        flesch_score, grade_level = readability_check(blog_content)
        blog_log['readability'] = {"flesch_score": flesch_score, "grade_level": grade_level}

        if flesch_score < 50 or grade_level > 8:
            blog_log['status'] = "readability_failed"
            verbose_print(f"⚠️ Blog readability too poor. Flesch: {flesch_score:.2f}, Grade Level: {grade_level:.2f}. Blog marked as failed.")

        structural_report, topic_report = quality_check(blog_content, prompts_dict, row['Topic'], blog_log)
        blog_log['qa_reports'] = {"structural": structural_report, "topic": topic_report}

        qa_pass = not ("fail" in structural_report.lower() or "fail" in topic_report.lower() or "missing" in structural_report.lower() or "missing" in topic_report.lower())

        if blog_log.get('status', 'failed') != "readability_failed" and qa_pass:
            blog_log['status'] = "passed"

        file_prefix = "__failed_" if blog_log.get('status', 'failed') != "passed" else ""
        generated_meta_description = generate_meta_description(row['Topic'], row['Primary Keyword'], blog_log)
        front_matter = build_front_matter(row['Meta Title'], generated_meta_description, row['Slug'], row['Keywords'])
        filepath = os.path.join(OUTPUT_DIR, f"{file_prefix}{row['Slug']}.md")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(front_matter)
            f.write(blog_content.strip())

        if blog_log['status'] == "passed":
            log_passed_blog(row)
            verbose_print(f"✅ Blog saved successfully (PASSED QA): {filepath}")
        else:
            log_failed_blog(row, "QA Failure or Readability Failure")
            verbose_print(f"⚠️ Blog saved but FAILED QA/Readability: {filepath}")

        save_json_log(row['Slug'], blog_log)
    except Exception as e:
        verbose_print(f"❌ Blog generation crashed for topic '{row.get('Topic', 'Unknown')}': {str(e)}")
        log_failed_blog(row, f"Fatal error during blog generation: {e}")

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
