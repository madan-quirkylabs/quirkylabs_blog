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
import random  # ensure this is already at the top
import yaml

from core.llm_router import call_llm  # 🔄 updated to use call_llm

# Setup project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load internal modules
from utils.paths import INPUT_DIR, SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, SECTION_PROMPTS_PATH, RETRIES_DIR
from config.config_loader import load_config, load_pillar_config

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load config and OpenAI client
config = load_config()
pillar_config = load_pillar_config()

# Flag to enable or disable validation during generation
ENABLE_VALIDATION = False
ENABLE_RETRIES = False

# Ensure output dirs exist
for dir_path in [SUCCESS_DIR, FAILURE_DIR, LOGS_DIR, RETRIES_DIR]:
    os.makedirs(dir_path, exist_ok=True)

def sanitize_slug(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)        # remove punctuation
    text = re.sub(r"[\s_]+", "-", text)         # replace spaces/underscores with hyphens
    text = re.sub(r"-+", "-", text).strip("-")  # collapse multiple dashes and trim
    return text


# Load input CSV
input_path = os.path.join(INPUT_DIR, "sample_input.csv")
df = pd.read_csv(input_path)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
df["slug"] = df["slug"].apply(sanitize_slug)

# Load prompts
with open(SECTION_PROMPTS_PATH, "r", encoding="utf-8") as f:
    prompts_dict = yaml.safe_load(f)

faq_section_defs = prompts_dict.get("faq_sections", [])
faq_section_keys = [fs["key"] for fs in faq_section_defs]

SECTION_ENABLE_FLAGS = {
    key: section.get("enabled", True)
    for key, section in prompts_dict.items()
    if isinstance(section, dict) and "prompt" in section  # excludes faq_sections list
}
for faq_section in faq_section_defs:
    SECTION_ENABLE_FLAGS[faq_section["key"]] = faq_section.get("enabled", True)

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

external_links = """
## Trusted ADHD Resources

Here are some ADHD resources from reputable organizations:

- [CHADD – Children and Adults with ADHD](https://chadd.org)
- [ADDitude Magazine](https://www.additudemag.com)
- [CDC – ADHD Resources](https://www.cdc.gov/ncbddd/adhd)
- [ADHD Foundation (UK)](https://www.adhdfoundation.org.uk)
- [Understood.org – For Neurodiverse Learning](https://www.understood.org)
- [Mayo Clinic – ADHD Overview](https://www.mayoclinic.org/diseases-conditions/adhd)
"""

def interpolate_prompt(prompt, topic, primary_keyword):
    return (prompt.replace("{{Topic}}", topic)
                 .replace("{{topic}}", topic)
                 .replace("{{Primary Keyword}}", primary_keyword)
                 .replace("{{primary_keyword}}", primary_keyword))

def generate_faq_questions(section_key, topic, keyword):
    faq_def = next(item for item in faq_section_defs if item["key"] == section_key)
    prompt = faq_def["prompt"].replace("{{Topic}}", topic).replace("{{topic}}", topic)
    prompt = prompt.replace("{{Primary Keyword}}", keyword).replace("{{primary_keyword}}", keyword)
    system_instruction = faq_def["system_instruction"]

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    raw = call_llm(messages, section=section_key)

    raw_lines = raw.strip().split("")
    questions = [
        line.strip("-•* 1234567890. ").strip().strip('"').strip("'")
        for line in raw_lines
        if "?" in line and len(line.strip()) > 5
    ]
    return questions

def generate_answer_for_question(question):
    section = "faq_core"
    section_prompt = prompts_dict[section]

    prompt = section_prompt["prompt"].replace("{{Topic}}", question).replace("{{topic}}", question)
    messages = [
        {"role": "system", "content": section_prompt["system_instruction"]},
        {"role": "user", "content": prompt}
    ]
    return call_llm(messages, section=section)

def generate_faq_section(section_key, topic, keyword):
    questions = generate_faq_questions(section_key, topic, keyword)
    faq_blocks = []

    for question in questions:
        # Remove any accidental <summary> wrapping
        question = re.sub(r"</?summary>", "", question, flags=re.IGNORECASE).strip()
        answer = generate_answer_for_question(question)
        faq_blocks.append(f"<details><summary>{question}</summary><p>{answer.strip()}</p></details>")

    return "\n".join(faq_blocks)

def generate_section(section, topic, primary_keyword):
    prompt = prompts_dict.get(section, {}).get("prompt")
    system_instruction = prompts_dict.get(section, {}).get("system_instruction")

    if not prompt or not system_instruction:
        raise KeyError(f"Prompt or system_instruction missing for section '{section}'")

    prompt = prompt.replace("{{Topic}}", topic).replace("{{topic}}", topic)
    prompt = prompt.replace("{{Primary Keyword}}", primary_keyword).replace("{{primary_keyword}}", primary_keyword)

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    return call_llm(messages, section=section)

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

    for q, a in matches[:5]:
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
    related_slugs = [slug for slug in related_slugs if slug != current_slug]

    if not related_slugs:
        return ""

    # Shuffle and select top 8 related blogs
    random.shuffle(related_slugs)
    selected_slugs = related_slugs[:8]

    links = []
    for slug in selected_slugs:
        title = slug.replace("-", " ").title()
        links.append(f"- [{title}](/pages/{slug}/)")

    return f"""
<details>
<summary><strong>Explore More in This Series</strong></summary>

{chr(10).join(links)}
</details>
"""

def build_front_matter(meta_title, meta_desc, slug, keywords):
    def escape_quotes(text):
        return text.replace('"', '\\"').strip()

    today = datetime.utcnow().strftime('%Y-%m-%d')
    clean_title = escape_quotes(meta_title)
    clean_desc = escape_quotes(meta_desc)
    kws = "[" + ", ".join(f'\"{k.strip()}\"' for k in keywords.split(",") if k.strip()) + "]"

    return f"""---
title: \"{clean_title}\"
description: \"{clean_desc}\"
slug: \"{slug}\"
date: {today}
draft: false
type: \"page\"
categories: [\"ADHD Guides\"]
tags: {kws}
keywords: {kws}
og_image: \"/og/{slug}.png\"
og_title: "{clean_title}"
og_description: "{clean_desc}"
---\n\n"""

def assemble_blog(sections, row):
    try:
        all_faq_html = "\n\n".join([
            f"\n\n### {f['heading']}\n\n{sections[f['key']]}"
            for f in faq_section_defs if f['key'] in sections
        ])

        faq_structured = faq_to_jsonld(all_faq_html)
        related_block = render_related_spokes(row['pillar_slug'], row['slug'])

        article_structured = json.dumps({
            "@context": "https://schema.org",
            "@type": "Article",
            "author": {
                "@type": "Person",
                "name": "QuirkyLabs",
                "url": "https://quirkylabs.ai/about"
            },
            "headline": row["meta_title"],
            "mainEntityOfPage": f"https://blog.quirkylabs.ai/pages/{row['slug']}/",
            "datePublished": datetime.utcnow().strftime('%Y-%m-%d')
        }, indent=2)

        breadcrumb_structured = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Home",
                    "item": "https://quirkylabs.ai/"
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "Blog",
                    "item": "https://blog.quirkylabs.ai/"
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": row["meta_title"],
                    "item": f"https://blog.quirkylabs.ai/pages/{row['slug']}/"
                }
            ]
        }, indent=2)

    except Exception as e:
        print(f"[assemble_blog] Error building schemas: {e}")
        raise

    try:
        return f"""
{sections.get('emotional_hook', '*[This section was skipped]*')}

{sections.get('story_part_1', '*[This section was skipped]*')}

{sections.get('story_part_2', '*[This section was skipped]*')}

{sections.get('story_part_3', '*[This section was skipped]*')}

## Quickfire ADHD Checklist

{sections.get('checklist', '*[This section was skipped]*')}

## Frequently Asked Questions

{all_faq_html}

{related_block}

{external_links}

---

**Written by our research team from [QuirkyLabs.ai](https://quirkylabs.ai)**  
Alex builds ADHD-friendly productivity tools with stories, science, and squirrels.  
[Learn more →](https://quirkylabs.ai)

---

<script type="application/ld+json">
{faq_structured}
</script>

<script type="application/ld+json">
{article_structured}
</script>

<script type="application/ld+json">
{breadcrumb_structured}
</script>

"""
    except Exception as e:
        print(f"[assemble_blog] Error constructing blog body: {e}")
        raise

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

def get_related_slug_map(pillar_slug, current_slug):
    spokes = pillar_config.get(pillar_slug, {}).get("spokes", [])
    links = {}
    for slug in spokes:
        if slug == current_slug:
            continue
        anchor = slug.replace("-", " ").title()
        url = f"/pages/{slug}/"
        links[slug] = {"anchor": anchor, "url": url}
    return links

def enforce_keyword_presence(text, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    if not pattern.search(text):
        return f"{keyword}: {text}"
    return text

def generate_meta_description(topic, keyword, blog_content):
    section = "meta_description"
    prompt_template = prompts_dict.get(section, {}).get("prompt")
    instruction = prompts_dict.get(section, {}).get("system_instruction")
    prompt = prompt_template.replace("{{Topic}}", topic).replace("{{Primary Keyword}}", keyword)
    prompt = prompt.replace("{{topic}}", topic).replace("{{primary_keyword}}", keyword)
    prompt = prompt.replace("{{Content}}", blog_content[:800])

    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": prompt}
    ]
    return call_llm(messages, section=section)

def generate_emotional_meta_title(topic, keyword):
    section = "meta_title"
    prompt_template = prompts_dict.get(section, {}).get("prompt")
    instruction = prompts_dict.get(section, {}).get("system_instruction")

    prompt = prompt_template.replace("{{Topic}}", topic).replace("{{Primary Keyword}}", keyword)
    prompt = prompt.replace("{{topic}}", topic).replace("{{primary_keyword}}", keyword)

    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": prompt}
    ]
    return call_llm(messages, section=section)

def insert_sentence_into_section(section_text, sentence):
    paras = section_text.strip().split("\n\n")
    if len(paras) > 2:
        paras.insert(2, sentence)
    else:
        paras.append(sentence)
    return "\n\n".join(paras)

def generate_story_section_with_link(section_name, topic, keyword, pillar_slug, current_slug, generate_func):
    section_text = generate_func(section_name, topic, keyword)

    if section_name not in ["story_part_2", "story_part_3"]:
        return section_text

    slug_map = get_related_slug_map(pillar_slug, current_slug)
    if not slug_map:
        return section_text  # No links to inject

    # fallback static
    fallback = next(iter(slug_map.values()))
    static = f"You might also want to check out [{fallback['anchor']}]({fallback['url']})."
    return insert_sentence_into_section(section_text, static)

def generate_keywords_from_blog(topic, blog_body):
    section = "keyword_generation"
    prompt_template = prompts_dict[section]["prompt"]
    system_instruction = prompts_dict[section]["system_instruction"]

    prompt = prompt_template.replace("{{Topic}}", topic).replace("{{Content}}", blog_body[:1500])

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt}
    ]

    try:
        return call_llm(messages, section=section)
    except Exception as e:
        print(f"[KeywordGen] Error: {e}")
        return "ADHD, Neurodivergence"

def check_readability(text):
    return textstat.flesch_reading_ease(text), textstat.flesch_kincaid_grade(text)

def generate_blog(row):
    topic = row["topic"]
    keyword = row["primary_keyword"]
    slug = row["slug"]

    if SECTION_ENABLE_FLAGS.get("meta_title", True):
        meta_title = generate_emotional_meta_title(topic, keyword)
        meta_title = enforce_keyword_presence(meta_title, keyword)
    else:
        meta_title = topic
    keywords = row.get("keywords", "")

    sections = {}
    log = {"slug": slug, "topic": topic, "status": "in_progress", "section_attempts": []}

    try:
        for section in section_order:
            if not SECTION_ENABLE_FLAGS.get(section, True):
                print(f"⏭️ Skipping section: {section}")
                continue
            success = False
            log["section_attempts"].append({"section": section, "attempts": []})

            for attempt in range(config["openai"]["max_retries"]):
                try:
                    if section in FAQ_TYPES:
                        content = generate_faq_section(section, topic, keyword)
                    elif section in ["story_part_2", "story_part_3"]:
                        content = generate_story_section_with_link(
                            section_name=section,
                            topic=topic,
                            keyword=keyword,
                            pillar_slug=row.get("pillar_slug", ""),
                            current_slug=row.get("slug", ""),
                            generate_func=generate_section
                        )
                    else:
                        content = generate_section(section, topic, keyword)
                    sections[section] = content
                    log["section_attempts"][-1]["attempts"].append({"status": "success"})
                    success = True
                    break

                except Exception as e:
                    print(e)
                    log["section_attempts"][-1]["attempts"].append({"status": "fail", "error": str(e)})

            if not success:
                log["status"] = "failed_section"
                save_log(slug, log)
                if ENABLE_RETRIES:
                    save_retry_payload(row, section)
                return

        row["meta_title"] = meta_title
        blog = assemble_blog(sections, row)

        if SECTION_ENABLE_FLAGS.get("keyword_generation", True):
            generated_keywords = generate_keywords_from_blog(topic, blog)

            gpt_keywords = [kw.strip() for kw in generated_keywords.split(",") if kw.strip()]
            keywords = ",".join(gpt_keywords[:7])
        else:
            keywords = row.get("keywords", "")

        if ENABLE_VALIDATION:
            flesch, grade = check_readability(blog)
            log["readability"] = {"flesch": flesch, "grade": grade}

        if SECTION_ENABLE_FLAGS.get("meta_description", True):
            meta_desc = generate_meta_description(topic, keyword, blog)
            meta_desc = enforce_keyword_presence(meta_desc, keyword)
        else:
            meta_desc = ""

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
