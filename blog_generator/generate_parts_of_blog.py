import os
import json
from glob import glob
from core.llm_client import call_llm
from core.config import load_config

SPOKE_METADATA_ROOT = os.path.join("config", "spoke-metadata")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output", "success")

GENERATE_META_FOR_ARTICLE_PROMPT = """
Act as QuirkyLabs' Chief Neural Architect. Generate SEO-optimized metadata for the ADHD spoke article with slug: '{spoke_slug}'.

---

### 🔧 **STRICT VALIDATION RULES**  
1. **REJECT ANY OUTPUT** containing square brackets `[]` (except for lists).  
2. **NEVER USE GENERIC PLACEHOLDERS** like "[Pain]" or "[Struggle]" - extract specifics from `{spoke_slug}`.  
3. **ENFORCE NEURO-MECHANISM CONSISTENCY**: The same term (e.g., "dopamine dip") must appear in title, description, and og_description.  

---

### 🧠 **TITLE (Pick ONE format)**  
**A. Diagnostic (For How-To Content):**  
`"ADHD & [EXPLICIT_PAIN_POINT]: The [NEURO_MECHANISM] Sabotaging Your [LIFE_AREA] (Debug It)"`  
→ Example: `"ADHD & Bill Avoidance: Your Brain’s Amygdala Freeze (Debug It)"`  

**B. Emotional (For Stigma-Busting):**  
`"[COMMON_MISLABEL] Isn’t Laziness—It’s Your Brain’s [NEURO_MECHANISM] in Overdrive"`  
→ Example: `"Budget Procrastination Isn’t Laziness—It’s Your Dopamine Dip in Overdrive"`  

**Validation Checks**:  
- `EXPLICIT_PAIN_POINT` must match `{spoke_slug}` (e.g., "financial-chaos" → "Money Avoidance")  
- `NEURO_MECHANISM` must be from approved list:  
  ```python
  ["dopamine dip", "amygdala freeze", "RSD hypervigilance", "executive dysfunction loop", "time blindness", "attention tunneling"]
  ```  

---

### 📝 **DESCRIPTION (155–165 chars)**  
**Template**:  
`"[SENSORY_METAPHOR]? [STUDY_CITATION] proves [NEURO_MECHANISM] blocks [ACTION]. [BRAND_CTA]."`  

**Validation Rules**:  
1. **SENSORY_METAPHOR** must be visceral:  
   ✅ `"Does checking your bank account feel like touching a hot stove?"`  
   ❌ `"Struggling with money?"`  
2. **STUDY_CITATION** must include year:  
   ✅ `"Dodson 2019"`, `"Faraone et al., 2021"`  
3. **BRAND_CTA** must include:  
   ✅ `"Neuro-Action Checklist"`, `"Neuro-OS upgrade"`  

---

### 🗂️ **DYNAMIC FIELDS**  
**Categories (3 required)**:  
```python
# Pre-approved list (extracted from your content hub)
CATEGORIES = [
    "ADHD Emotional Regulation", "Executive Dysfunction", "ADHD at Work", 
    "ADHD and Money", "ADHD Productivity", "ADHD Relationships",
    "Rejection Sensitivity", "Financial Avoidance",
    "ADHD Nutrition", "ADHD Hygiene", "ADHD Relationships",
    "Self-Compassion", "Attachment Patterns",
    "Sensory Processing", "Neurodivergent Identity", "ADHD Diagnosis",
    "Burnout & Fatigue"
]
```  

**Tags (6 required)**:  
- First 3 must include:  
  1. The neuro-mechanism (e.g., "dopamine")  
  2. The pain point (e.g., "financial avoidance")  
  3. One emotional term (e.g., "shame", "overwhelm")  

**Keywords (6 required)**:  
- Must include:  
  1. One "why" question (`"why do ADHDers struggle with [TOPIC]"`)  
  2. One "how to" query (`"how to [ACTION] with ADHD"`)  
  3. One tool/phrase (`"ADHD YNAB setup"`)  

---

### 🎨 **OG FIELDS**  
**og_image Path**:  
```python
f"/og/adhd-{slugify(pain_point)}-debug.png"  # e.g., "/og/adhd-bill-avoidance-debug.png"
```  

**og_title**:  
- Max 60 chars  
- Must include neuro-mechanism  

**og_description**:  
- Max 120 chars  
- Must include:  
  ✅ Problem (`"Dopamine deserts"`)  
  ✅ Solution (`"Neuro-actions"`)  

---

### ✨ **EXAMPLE OUTPUT**  
```markdown
---
title: "ADHD & Bill Avoidance: Your Brain’s Amygdala Freeze (Debug It)"
description: "Does checking your bank account feel like touching a hot stove? Dodson 2019 proves amygdala freeze blocks financial tasks. Upgrade your Neuro-OS."
slug: "adhd-financial-chaos"
author: "Madan | QuirkyLabs"
date: "2025-06-23"
type: "page"
categories: ["ADHD and Money", "Executive Dysfunction", "Financial Avoidance"]
tags: ["amygdala freeze", "financial avoidance", "shame", "RSD", "bill paralysis", "adulting"]
keywords: ["why do ADHDers avoid bills", "how to pay bills with ADHD", "ADHD money shame", "ADHD YNAB setup", "financial trauma ADHD", "amygdala freeze money"]
og_image: "/og/adhd-bill-avoidance-debug.png"
og_title: "ADHD Bill Avoidance: Amygdala Freeze Fix"
og_description: "Amygdala freeze blocking bills? Neuro-actions for financial safety."
---
```

---

### 🚨 **VALIDATION FAILURE MODE**  
If constraints aren’t met, return this error template:  
```python
raise ValueError(
    f"VALIDATION FAILED: Missing required elements in field '{failed_field}'. "
    f"Expected {requirement} but got '{actual_value}'. "
    "Rewrite with stricter adherence to neuro-mechanism consistency."
)
```
"""

STRUCTURED_FAQ_PROMPT = """
Act as QuirkyLabs' Neuro-Content Architect. Generate a **categorized FAQ schema** for the ADHD spoke article using this metadata:  
{spoke_metadata}

---

### **RULES**  
1. **Extract Directly From Metadata**:  
   - Use `spoke_specific_pain_point` for raw ADHD language (e.g., "involuntary ghosting").  
   - Cite studies from `pillar_specific_research.studies` (include author/year).  
   - Integrate QuirkyLabs tools from `solution_war_room` or `content_arsenal`.  

2. **Required Categories** (Include 3-5):  
   - **Neuro-Why**: *"What’s happening in my brain?"*  
   - **Shame Disruptors**: *"Is this my fault?"*  
   - **Practical Hacks**: *"What can I do RIGHT NOW?"*  
   - **Social Scripts**: *"How do I explain this to others?"*  
   - **Advanced Tools**: *"How can QuirkyLabs help?"*  

3. **Question Templates**:  
   - **For Neuro-Why**:  
     *"Why does [pain_point] feel like [sensory_metaphor]?"*  
     *"How is this different from just [neurotypical_behavior]?"*  
   - **For Shame Disruptors**:  
     *"Am I [negative_self_label] because I [ADHD_behavior]?"*  
     *"Does everyone with ADHD struggle with this?"*  
   - **For Practical Hacks**:  
     *"What’s the first step when [pain_point] hits?"*  
     *"How do I [action] when I’m in ‘Spoonie Mode’?"*  

---

### **EXAMPLE OUTPUT**  
```markdown
### **Comprehensive FAQ: [Spoke Title]**  

#### **Category 1: Neuro-Why**  
**Q: Why does [pain_point] trigger [physical/emotional reaction]?**  
**A:** [Study citation] shows this is your brain’s [neuro-mechanism] in overdrive. Example: *"Dodson (2019) links ‘involuntary ghosting’ to amygdala freeze + dopamine dips when task-switching."*  

**Q: Is this just [misconception] or an ADHD thing?**  
**A:** No! [Study] proves ADHD brains process [task] differently. *"Semrud-Clikeman (2012) found prefrontal-amygdala dysregulation in [context]."*  

#### **Category 2: Shame Disruptors**  
**Q: Am I [shame_label] because I can’t [action]?**  
**A:** This is a **neurobiological barrier**, not a moral failing. Your [brain_region] is overloaded by [trigger]. Try our [tool_name] to rewire this.  

#### **Category 3: Practical Hacks**  
**Q: What’s the ‘Good Enough’ fix for [pain_point]?**  
**A:** Use the [QuirkyLabs protocol]:  
1. [Micro-action]  
2. [Dopamine-paired reward]  
3. [Sensory cue]  

#### **Category 4: Social Scripts**  
**Q: How do I explain [behavior] to my [person]?**  
**A:** AI-generated script: *"[Partner], my ADHD brain [neuro-mechanism]. Can we try [accommodation]?"*  

#### **Category 5: Advanced Tools**  
**Q: How does [QuirkyLabs tool] short-circuit [pain_point]?**  
**A:** It uses [neuro-strategy] to bypass [brain_region] blockage. Example: *"‘Reply Roulette’ gamifies texting to reduce amygdala activation."*  
```

---

### **DYNAMIC INSTRUCTIONS**  
1. **For Emotional Topics** (e.g., RSD, shame):  
   - Lead with **Shame Disruptors**. Use phrases like *"This isn’t laziness—it’s [neuro-mechanism]."*  
2. **For Task Paralysis**:  
   - Include **"Spoonie Mode" hacks** (e.g., *"The 1% Rule: Just [tiny_action]."*).  
3. **Always End with Hope**:  
   - Final category must be **Advanced Tools**, showcasing a QuirkyLabs solution.  

---

### **VALIDATION CHECKS**  
- Reject answers without:  
  1. A **study citation** or **neuro-mechanism**.  
  2. A **validation phrase** (e.g., *"This is common with ADHD because..."*).  
  3. A **QuirkyLabs tool/prompt**.  
- Use **ADHD community slang** (e.g., "Spoonie Mode," "task paralysis").  
```

---

### **Key Features**  
1. **Pain-Point Precision**: Pulls visceral metaphors from `pain_autopsy_details` (e.g., *"amygdala freeze"*).  
2. **Scientific Rigor**: Auto-attaches the most relevant study from your metadata.  
3. **Branded Solutions**: Weaves in tools like *"Reply Roulette"* or *"Neuro-Communication Protocol"*.  

"""

def discover_spoke_metadata():
    """
    Discover all spoke metadata files, extract pillar and spoke slugs, and load their JSON content.
    Returns a list of dicts: {pillar_slug, spoke_slug, metadata}
    Only the first two spokes (alphabetically) per pillar are included.
    """
    base_dir = os.path.join(os.path.dirname(__file__), SPOKE_METADATA_ROOT)
    all_spoke_entries = []
    for pillar_dir in os.listdir(base_dir):
        pillar_path = os.path.join(base_dir, pillar_dir)
        if not os.path.isdir(pillar_path):
            continue
        # Collect all spoke metadata files for this pillar
        spoke_files = [fname for fname in os.listdir(pillar_path)
                       if fname.startswith("spoke-metadata.") and fname.endswith(".json")]
        spoke_files.sort()  # Alphabetical order
        for fname in spoke_files:  # Only first two
            spoke_slug = fname[len("spoke-metadata."):-len(".json")]
            spoke_path = os.path.join(pillar_path, fname)
            with open(spoke_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            all_spoke_entries.append({
                "pillar_slug": pillar_dir,
                "spoke_slug": spoke_slug,
                "metadata": metadata
            })
    return all_spoke_entries


def generate_faq_prompt(example_faq_path, spoke_metadata):
    """
    Construct a one-shot prompt for Gemini using the full example FAQ and the current spoke metadata.
    """
    # Load the example FAQ markdown
    with open(example_faq_path, "r", encoding="utf-8") as f:
        example_faq = f.read()
    # Convert spoke metadata to pretty JSON
    spoke_json = json.dumps(spoke_metadata, indent=2, ensure_ascii=False)
    # Construct the prompt
    prompt = (
        f"{STRUCTURED_FAQ_PROMPT}\n\n"
        "Now, generate a comprehensive FAQ section for this spoke_metadata (output only the FAQ section in markdown):\n\n"
        f"{spoke_json}"
    )
    return prompt


def write_faq_to_file(pillar_slug, spoke_slug, faq_markdown):
    out_dir = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "faq.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(faq_markdown)


def faq_file_exists(pillar_slug, spoke_slug):
    out_path = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug, "faq.md")
    return False
    # return os.path.exists(out_path)


def faq_ldjson_file_exists(pillar_slug, spoke_slug):
    out_path = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug, "faq-ldjson.md")
    return False
    return os.path.exists(out_path)


def generate_faq_ldjson(pillar_slug, spoke_slug, config):
    out_dir = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug)
    faq_path = os.path.join(out_dir, "faq.md")
    ldjson_path = os.path.join(out_dir, "faq-ldjson.md")
    if not os.path.exists(faq_path):
        print(f"  ⚠️  Skipping FAQ-LDJSON (faq.md missing) for Pillar: {pillar_slug} | Spoke: {spoke_slug}")
        return False
    if os.path.exists(ldjson_path):
        print(f"  Skipping existing FAQ-LDJSON for Pillar: {pillar_slug} | Spoke: {spoke_slug}")
        return False
    with open(faq_path, "r", encoding="utf-8") as f:
        faq_content = f.read()
    prompt = (
        "Convert the following FAQ markdown into a valid application/ld+json (schema.org FAQPage) format. "
        "Output only the JSON-LD code block, nothing else.\n\n"
        f"{faq_content}"
    )
    messages = [
        {"role": "system", "content": "You are a schema.org FAQPage expert. Output only the JSON-LD code block."},
        {"role": "user", "content": prompt}
    ]
    try:
        ldjson = call_llm(messages, provider="gemini", section_config=config)
        with open(ldjson_path, "w", encoding="utf-8") as f:
            f.write(ldjson)
        print(f"  ✅ FAQ-LDJSON generated for Pillar: {pillar_slug} | Spoke: {spoke_slug}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to generate FAQ-LDJSON for Pillar: {pillar_slug} | Spoke: {spoke_slug}: {e}")
        return False


def generate_meta_prompt(example_meta_path, spoke_metadata):
    """
    Construct a one-shot prompt for Gemini using the full example meta and the current spoke metadata.
    """
    # Load the example meta markdown
    with open(example_meta_path, "r", encoding="utf-8") as f:
        example_meta = f.read()
    # Convert spoke metadata to pretty JSON
    spoke_json = json.dumps(spoke_metadata, indent=2, ensure_ascii=False)
    # Construct the prompt
    prompt = (
        f"{GENERATE_META_FOR_ARTICLE_PROMPT}\n\n"
        "Now, generate a comprehensive meta section for this spoke_metadata (output only the meta section in markdown). "
        "The slug must match the spoke slug exactly. The meta must be highly SEO-optimized, as this is the main source of user engagement.\n\n"
        f"{spoke_json}"
    )
    return prompt


def meta_file_exists(pillar_slug, spoke_slug):
    out_path = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug, "meta.md")
    return os.path.exists(out_path)


def write_meta_to_file(pillar_slug, spoke_slug, meta_markdown):
    out_dir = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "meta.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(meta_markdown)


def meta_ldjson_file_exists(pillar_slug, spoke_slug):
    out_path = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug, "meta-ldjson.md")
    return os.path.exists(out_path)


def write_meta_ldjson_to_file(pillar_slug, spoke_slug, meta_ldjson):
    out_dir = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "meta-ldjson.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(meta_ldjson)


def generate_meta_ldjson(pillar_slug, spoke_slug, config, sample_meta_ldjson_path):
    out_dir = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug)
    meta_path = os.path.join(out_dir, "meta.md")
    ldjson_path = os.path.join(out_dir, "meta-ldjson.md")
    if not os.path.exists(meta_path):
        print(f"  ⚠️  Skipping META-LDJSON (meta.md missing) for Pillar: {pillar_slug} | Spoke: {spoke_slug}")
        return False
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_content = f.read()
    with open(sample_meta_ldjson_path, "r", encoding="utf-8") as f:
        sample_ldjson = f.read()
    prompt = (
        "Here is a sample meta-ldjson for a similar spoke:\n\n"
        f"{sample_ldjson}\n\n"
        "Here is the meta section for this spoke:\n\n"
        f"{meta_content}\n\n"
        "Now, generate a valid application/ld+json (schema.org) JSON-LD for this meta section, matching the style and structure of the sample. Output only the JSON-LD code block, nothing else."
    )
    messages = [
        {"role": "system", "content": "You are a schema.org meta JSON-LD expert. Output only the JSON-LD code block."},
        {"role": "user", "content": prompt}
    ]
    try:
        meta_ldjson = call_llm(messages, provider="gemini", section_config=config)
        write_meta_ldjson_to_file(pillar_slug, spoke_slug, meta_ldjson)
        print(f"  ✅ META-LDJSON generated for Pillar: {pillar_slug} | Spoke: {spoke_slug}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to generate META-LDJSON for Pillar: {pillar_slug} | Spoke: {spoke_slug}: {e}")
        return False


def generate_story_prompt(example_story_path, narrative_prompt_path, spoke_metadata):
    """
    Construct a prompt for Gemini using only the narrative prompt and the current spoke metadata.
    The prompt explicitly instructs Gemini to first semantically understand the provided spoke_metadata (in JSON), and to generate a story that is highly specific to the context, pain points, and details in the metadata.
    The sample story is NOT included. The LLM is explicitly told not to copy or reuse any content from the prompt or examples, and to use only the spoke_metadata for the story content.
    """
    # Load the narrative prompt
    with open(narrative_prompt_path, "r", encoding="utf-8") as f:
        narrative_prompt = f.read()
    # Convert spoke metadata to pretty JSON
    spoke_json = json.dumps(spoke_metadata, indent=2, ensure_ascii=False)
    # Construct the prompt
    prompt = (
        "You are given a JSON object called `spoke_metadata` that contains all the context, pain points, and details for a specific ADHD blog spoke.\n"
        "First, carefully read and semantically understand the `spoke_metadata` to grasp the unique context, challenges, and audience for this spoke.\n"
        "Then, generate a comprehensive, narrative-driven, science-backed ADHD article that is highly specific to the details in the `spoke_metadata`.\n"
        "The story must not be generic; it should directly address the pain points, situations, and nuances described in the metadata.\n"
        "Follow the rules and style in the narrative prompt below, but ensure all content is tailored to the current spoke.\n"
        "Do NOT copy or reuse any content from the prompt or any sample stories or examples. Only use the details from the `spoke_metadata` for the story content.\n"
        "Output only the story in markdown.\n\n"
        "Here is the narrative prompt to follow:\n\n"
        f"{narrative_prompt}\n\n"
        "Here is the spoke_metadata (in JSON):\n\n"
        f"{spoke_json}\n"
    )
    return prompt


def story_file_exists(pillar_slug, spoke_slug):
    out_path = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug, "story.md")
    return os.path.exists(out_path)


def write_story_to_file(pillar_slug, spoke_slug, story_markdown):
    out_dir = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "story.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(story_markdown)


if __name__ == "__main__":
    spokes = discover_spoke_metadata()
    if not spokes:
        print("No spokes found.")
        exit(1)
    example_faq_path = os.path.join(
        "blog-staging-area", "adhd-task-paralysis-focus", "why-does-every-task-feel-equally-urgent", "faq.md"
    )
    example_faq_path = os.path.join(os.path.dirname(__file__), example_faq_path)
    config = load_config()
    success_count = 0
    fail_count = 0
    skipped_count = 0
    ldjson_success = 0
    ldjson_fail = 0
    ldjson_skipped = 0
    for entry in spokes:
        if faq_file_exists(entry["pillar_slug"], entry["spoke_slug"]):
            print(f"Skipping existing FAQ for Pillar: {entry['pillar_slug']} | Spoke: {entry['spoke_slug']} ...")
            skipped_count += 1
        else:
            try:
                prompt = generate_faq_prompt(example_faq_path, entry["metadata"])
                messages = [
                    {"role": "system", "content": "You are an ADHD FAQ blog writer. Output only the FAQ markdown section."},
                    {"role": "user", "content": prompt}
                ]
                print(f"Generating FAQ for Pillar: {entry['pillar_slug']} | Spoke: {entry['spoke_slug']} ...")
                faq_markdown = call_llm(messages, provider="gemini", section_config=config)
                write_faq_to_file(entry["pillar_slug"], entry["spoke_slug"], faq_markdown)
                print("  ✅ Success\n")
                success_count += 1
            except Exception as e:
                print(f"  ❌ Failed: {e}\n")
                fail_count += 1
        # Now handle LDJSON
        result = generate_faq_ldjson(entry["pillar_slug"], entry["spoke_slug"], config)
        if result is True:
            ldjson_success += 1
        elif result is False and faq_ldjson_file_exists(entry["pillar_slug"], entry["spoke_slug"]):
            ldjson_skipped += 1
        else:
            ldjson_fail += 1
    print(f"\nDone! {success_count} FAQs generated, {skipped_count} skipped, {fail_count} failed.")
    print(f"LDJSON: {ldjson_success} generated, {ldjson_skipped} skipped, {ldjson_fail} failed.")

    # META GENERATION LOOP
    example_meta_path = os.path.join(
        "blog-staging-area", "adhd-task-paralysis-focus", "why-does-every-task-feel-equally-urgent", "meta.md"
    )
    example_meta_path = os.path.join(os.path.dirname(__file__), example_meta_path)
    meta_success = 0
    meta_fail = 0
    meta_skipped = 0
    for entry in spokes:
        if meta_file_exists(entry["pillar_slug"], entry["spoke_slug"]):
            print(f"Skipping existing META for Pillar: {entry['pillar_slug']} | Spoke: {entry['spoke_slug']} ...")
            meta_skipped += 1
            continue
        try:
            meta_prompt = generate_meta_prompt(example_meta_path, entry["metadata"])
            messages = [
                {"role": "system", "content": "You are an ADHD SEO meta expert. Output only the meta markdown section."},
                {"role": "user", "content": meta_prompt}
            ]
            print(f"Generating META for Pillar: {entry['pillar_slug']} | Spoke: {entry['spoke_slug']} ...")
            meta_markdown = call_llm(messages, provider="gemini", section_config=config)
            write_meta_to_file(entry["pillar_slug"], entry["spoke_slug"], meta_markdown)
            print("  ✅ META Success\n")
            meta_success += 1
        except Exception as e:
            print(f"  ❌ META Failed: {e}\n")
            meta_fail += 1
    print(f"META: {meta_success} generated, {meta_skipped} skipped, {meta_fail} failed.")

    # META-LDJSON GENERATION LOOP
    sample_meta_ldjson_path = os.path.join(
        "blog-staging-area", "adhd-task-paralysis-focus", "why-does-every-task-feel-equally-urgent", "meta-ldjson.md"
    )
    sample_meta_ldjson_path = os.path.join(os.path.dirname(__file__), sample_meta_ldjson_path)
    meta_ldjson_success = 0
    meta_ldjson_fail = 0
    meta_ldjson_skipped = 0
    for entry in spokes:
        result = generate_meta_ldjson(entry["pillar_slug"], entry["spoke_slug"], config, sample_meta_ldjson_path)
        if result is True:
            meta_ldjson_success += 1
        elif result is False and meta_ldjson_file_exists(entry["pillar_slug"], entry["spoke_slug"]):
            meta_ldjson_skipped += 1
        else:
            meta_ldjson_fail += 1
    print(f"META-LDJSON: {meta_ldjson_success} generated, {meta_ldjson_skipped} skipped, {meta_ldjson_fail} failed.")

    # STORY GENERATION LOOP (only first 2 spokes)
    story_success = 0
    story_fail = 0
    story_skipped = 0
    for entry in spokes[:2]:
        if story_file_exists(entry["pillar_slug"], entry["spoke_slug"]):
            print(f"Skipping existing STORY for Pillar: {entry['pillar_slug']} | Spoke: {entry['spoke_slug']} ...")
            story_skipped += 1
            continue
        try:
            story_prompt = generate_story_prompt(example_faq_path, example_meta_path, entry["metadata"])
            messages = [
                {"role": "system", "content": "You are an ADHD narrative blog expert. Output only the story markdown section."},
                {"role": "user", "content": story_prompt}
            ]
            print(f"Generating STORY for Pillar: {entry['pillar_slug']} | Spoke: {entry['spoke_slug']} ...")
            story_markdown = call_llm(messages, provider="gemini", section_config=config)
            write_story_to_file(entry["pillar_slug"], entry["spoke_slug"], story_markdown)
            print("  ✅ STORY Success\n")
            story_success += 1
        except Exception as e:
            print(f"  ❌ STORY Failed: {e}\n")
            story_fail += 1
    print(f"STORY: {story_success} generated, {story_skipped} skipped, {story_fail} failed.")

