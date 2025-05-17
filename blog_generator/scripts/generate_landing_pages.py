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

from utils.file_ops import save_section, load_section

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
    "faq_combined",
    "cta"
]

FAQ_TYPES = {
    "faq_google_autocomplete": {"style": "searchy"},
    "faq_core": {"style": "informational"},
    "faq_curious": {"style": "quirky"},
    "faq_cta": {"style": "cta"}
}

REQUIRED_YAML_KEYS = [
    "title", "description", "slug", "date", "draft", "type",
    "categories", "tags", "keywords", "og_image", "og_title", "og_description"
]

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

def generate_front_matter_from_one_call(row):
    section = "front_matter_one_shot"
    prompt_template = prompts_dict[section]["prompt"]
    system_instruction = prompts_dict[section]["system_instruction"]

    prompt = (
        prompt_template
        .replace("{{topic}}", row["topic"])
        .replace("{{primary_keyword}}", row["primary_keyword"])
        .replace("{{slug}}", row["slug"])
    )

    section_cfg = prompts_dict.get(section, {})
    messages = [
        {"role": "system", "content": section_cfg.get("system_instruction", "")},
        {"role": "user", "content": section_cfg.get("prompt", "").replace("{{topic}}", row["topic"]).replace("{{primary_keyword}}", row["primary_keyword"]).replace("{{slug}}", row["slug"])}
    ]
    raw_yaml = call_llm(messages, section=section, section_config=section_cfg)

    # ✅ Validate structure
    REQUIRED_YAML_KEYS = [
        "title", "description", "slug", "date", "draft", "type",
        "categories", "tags", "keywords", "og_image", "og_title", "og_description"
    ]

    try:
        # 🧹 Extract clean YAML between the first pair of ---
        if "---" in raw_yaml:
            parts = raw_yaml.split("---")
            if len(parts) >= 2:
                raw_yaml = "---\n" + parts[1].strip()  # Keep only the YAML block
            else:
                print("⚠️ LLM output had a starting '---' but no valid block after.")

        print("YAML output for front matter >>>>>>>>>>>>>> STARTS HERE")
        print(raw_yaml)
        print("YAML output for front matter <<<<<<<<<<<<<<<< ENDS HERE")

        parsed = yaml.safe_load(raw_yaml)
        if not isinstance(parsed, dict) or not all(k in parsed for k in REQUIRED_YAML_KEYS):
            raise ValueError("Missing required keys")

        # Enforce SEO constraints
        kw = row["primary_keyword"]
        slug = row["slug"]

        parsed["slug"] = slug
        if not parsed["title"].lower().startswith(kw.lower()):
            parsed["title"] = f"{kw}: {parsed['title']}"
        if kw.lower() not in parsed["description"].lower():
            parsed["description"] = f"{kw}: {parsed['description']}"

        parsed["og_title"] = parsed["title"]
        parsed["og_description"] = parsed["description"]
        parsed["og_image"] = f"/og/{slug}.png"

        return f"---\n{yaml.dump(parsed, sort_keys=False, allow_unicode=True)}---\n\n"

    except Exception as e:
        print(f"❌ Invalid front matter YAML: {e}")
        # fallback
        return f"""---
title: "Missing Title"
description: "Missing Description"
slug: "{row['slug']}"
date: {datetime.utcnow().strftime('%Y-%m-%d')}
draft: true
type: "page"
categories: ["ADHD Guides"]
tags: []
keywords: []
og_image: "/og/{row['slug']}.png"
og_title: "Missing Title"
og_description: "Missing Description"
---\n\n"""

def generate_combined_faq_section(topic, keyword, current_slug=None, pillar_slug=None, keyword_anchor_map=None):
    """
    Combine questions from multiple FAQ styles and format into a single markdown block with H3 headings.
    """

    question_sources = ["faq_search_queries", "faq_emotional", "faq_quirky"]

    all_questions = []

    # Collect questions from all configured sources
    for key in question_sources:
        try:
            questions = generate_faq_questions(key, topic, keyword)
            all_questions.extend(questions)
        except Exception as e:
            print(f"⚠️ Skipping {key} due to error: {e}")

    # Deduplicate questions by normalized text
    seen = set()
    unique_questions = []
    for q in all_questions:
        normalized = q.lower().strip("?!. ").replace("  ", " ")
        if normalized not in seen and len(q) > 8:
            seen.add(normalized)
            unique_questions.append(q)

    # Limit to top 10
    final_questions = unique_questions[:10]

    # Load related post slugs for internal linking
    related_slug_map = get_related_slug_map(pillar_slug, current_slug)

    faq_blocks = []

    for question in final_questions:
        raw_answer = generate_answer_for_question(question)
        enhanced = enhance_answer_formatting(raw_answer, question, related_slug_map, keyword_anchor_map)
        faq_blocks.append(f"### {question}\n\n{enhanced.strip()}")

    return "\n\n".join(faq_blocks)

def enhance_answer_formatting(answer, question, slug_map=None, keyword_map=None):
    # Shorten to ~2 sentences
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    short_answer = " ".join(sentences[:2])

    # Add Pro Tip if missing
    if "Pro Tip:" not in short_answer and len(sentences) > 2:
        short_answer += "\n\n**Pro Tip:** Try breaking it into tiny steps and reward progress."

    # Add internal link from slug map (based on question text)
    if slug_map:
        for slug, meta in slug_map.items():
            if slug.replace("-", " ") in question.lower():
                link = f"[{meta['anchor']}]({meta['url']})"
                short_answer += f"\n\nNeed more help? Check out {link}."
                break

    # ✅ Add internal links based on anchor phrases in the answer
    if keyword_map:
        for anchor, url in keyword_map.items():
            if anchor.lower() in short_answer.lower():
                pattern = re.compile(re.escape(anchor), re.IGNORECASE)
                short_answer = pattern.sub(f"[{anchor}]({url})", short_answer, count=1)
                break

    return short_answer

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

def faq_to_jsonld(faq_markdown):
    """
    Extracts top 5 FAQ questions and answers from markdown using H3 ### headers.
    Returns a valid FAQPage JSON-LD object.
    """
    import re
    from bs4 import BeautifulSoup

    faq_entries = []
    blocks = re.split(r"\n###\s+", faq_markdown)

    for block in blocks[1:]:  # skip first chunk before first ###

        # Split the block into Q and A
        lines = block.strip().split("\n", 1)
        if len(lines) != 2:
            continue  # skip malformed blocks

        question = lines[0].strip()
        answer_md = lines[1].strip()

        # Strip markdown formatting from answer
        answer_html = BeautifulSoup(answer_md, "html.parser").get_text().strip()

        faq_entries.append({
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": answer_html
            }
        })

        if len(faq_entries) >= 5:
            break

    jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faq_entries
    }

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

def assemble_blog_from_disk(slug, row):
    from utils.file_ops import load_section
    from datetime import datetime
    import json
    import re
    from bs4 import BeautifulSoup

    def read(section_name):
        return load_section(slug, section_name) or "*[This section was skipped]*"

    sections = {
        "emotional_hook": read("emotional_hook"),
        "story_part_1": read("story_part_1"),
        "story_part_2": read("story_part_2"),
        "story_part_3": read("story_part_3"),
        "checklist": read("checklist")
    }

    all_faq_html = sections.get("faq_combined", "")

    # render related links
    related_block = render_related_spokes(row['pillar_slug'], row['slug'])

    # FAQ structured schema
    faq_structured = faq_to_jsonld(all_faq_html)

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
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://quirkylabs.ai/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://blog.quirkylabs.ai/"},
            {"@type": "ListItem", "position": 3, "name": row["meta_title"], "item": f"https://blog.quirkylabs.ai/pages/{row['slug']}/"}
        ]
    }, indent=2)

    blog_body = f"""
{sections['emotional_hook']}

{sections['story_part_1']}

{sections['story_part_2']}

{sections['story_part_3']}

## Quickfire ADHD Checklist

{sections['checklist']}

## Frequently Asked Questions

{all_faq_html}

{related_block}

{external_links}

---

**Written by our research team from [QuirkyLabs.ai](https://quirkylabs.ai)**  
Alex builds ADHD-friendly productivity tools with stories, science, and squirrels.  
[Learn more →](https://quirkylabs.ai)

---

<script type="application/ld+json">{faq_structured}</script>
<script type="application/ld+json">{article_structured}</script>
<script type="application/ld+json">{breadcrumb_structured}</script>
"""
    return blog_body

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

def check_readability(text):
    return textstat.flesch_reading_ease(text), textstat.flesch_kincaid_grade(text)

def generate_blog(row):
    topic = row["topic"]
    keyword = row["primary_keyword"]
    slug = row["slug"]

    # Step 1: Load related slugs from the row
    related_slugs = [s.strip() for s in row.get("related_slugs", "").split(",") if s.strip()]

    # Step 2: Load pillar config with anchor info
    with open("config/prompts/pillar_config_with_anchors.json", "r", encoding="utf-8") as f:
        pillar_config = json.load(f)

    # Step 3: Build slug → anchors lookup
    slug_to_anchors = {}
    for cluster in pillar_config.values():
        for spoke in cluster["spokes"]:
            slug = spoke["slug"]
            anchors = spoke.get("preferred_internal_anchors") or [spoke.get("anchor")]
            slug_to_anchors[slug] = anchors

    # Step 4: Build keyword-anchor map scoped to this blog
    keyword_anchor_map = {}
    for rel_slug in related_slugs:
        for anchor in slug_to_anchors.get(rel_slug, []):
            keyword_anchor_map[anchor] = f"/pages/{rel_slug}/"

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
                    if section == "faq_combined":
                        content = generate_combined_faq_section(
                            topic=topic,
                            keyword=keyword,
                            current_slug=slug,
                            pillar_slug=row.get("pillar_slug", ""),
                            keyword_anchor_map=keyword_anchor_map
                        )
                    elif section in ["story_part_2", "story_part_3"]:
                        content = generate_story_section_with_link(
                            section_name=section,
                            topic=topic,
                            keyword=keyword,
                            pillar_slug=row.get("pillar_slug", ""),
                            current_slug=slug,
                            generate_func=generate_section
                        )
                    else:
                        content = generate_section(section, topic, keyword)
                    
                    existing = load_section(slug, section)
                    if existing:
                        sections[section] = existing
                        print(f"✅ Skipping {section}, already exists for {slug}")
                        continue

                    # after generating `content`
                    save_section(slug, section, content)
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

        row["meta_title"] = f"[SEO One-Shot] {topic}"
        blog = assemble_blog_from_disk(slug, row)

        # 🔥 Generate full front matter block in one LLM call
        if SECTION_ENABLE_FLAGS.get("front_matter_one_shot", True):
            front = generate_front_matter_from_one_call(row)

            # 📝 Save raw front matter for debugging
            debug_front_path = os.path.join(LOGS_DIR, f"{slug}_front_matter.yaml")
            with open(debug_front_path, "w", encoding="utf-8") as f:
                f.write(front)

            save_section(slug, "front_matter", front, ext="yaml")
        else:
            print(f"⚠️ Skipping front_matter_one_shot section as per config.")
            front = f"""---
                title: "Missing Title"
                description: "Missing Description"
                slug: "{slug}"
                date: {datetime.utcnow().strftime('%Y-%m-%d')}
                draft: true
                type: "page"
                categories: ["ADHD Guides"]
                tags: []
                keywords: []
                og_image: "/og/{slug}.png"
                og_title: "Missing Title"
                og_description: "Missing Description"
                ---\n\n"""

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
