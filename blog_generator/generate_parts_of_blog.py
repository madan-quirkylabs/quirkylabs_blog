import os
import json
from glob import glob
from core.llm_client import call_llm
from core.config import load_config

SPOKE_METADATA_ROOT = os.path.join("config", "spoke-metadata")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output", "success")

GENERATE_META_FOR_ARTICLE_PROMPT = """
---

### **Ultimate Gemini Prompt for ADHD Metadata Generation**  
**Role & Goal:**  
*You are a neuro-savvy content strategist for QuirkyLabs, crafting metadata that blends scientific rigor, emotional resonance, and SERP dominance. Your output must:*  
1. **Mirror the spoke’s pain point** (e.g., task-switching pain, digital overwhelm).  
2. **Leverage neurobiological insights** from the research studies in the spoke metadata.  
3. **Align with QuirkyLabs’ "Operating System for ADHD Brains" brand voice** (game-based, shame-free, dopamine-aware).  

**Input Template:**  
```markdown
"adhd-[TOPIC]-[SUBTOPIC].[QUESTION-FORMAT-SLUG]"  
Example: "adhd-task-paralysis-focus.why-is-switching-tasks-so-mentally-painful"  
```  

**Output Requirements:**  
1. **Title:**  
   - Include:  
     - **Primary pain point** (e.g., "mentally painful task-switching").  
     - **Neuro-mechanism** (e.g., "dopamine cliffs," "fronto-striatal circuits").  
     - **Empowering twist** (e.g., "hack your brain’s OS").  
   - Formats:  
     - **Diagnostic**: "ADHD & [Pain]: Why [Specific Struggle] Feels Like [Vivid Metaphor]".  
     - **Emotional**: "[Struggle] Isn’t Your Fault—It’s Your Brain’s [Neuro-Mechanism]".  
     - **Solution**: "How to [Action] When Your ADHD Brain [Pain Point]".  

2. **Description:**  
   - Structure:  
     - **Hook**: Validate the visceral struggle (e.g., "That ‘brain grind’ when switching tasks?").  
     - **Neuro-proof**: Cite a study/mechanism (e.g., "Dopamine dysregulation makes disengagement agonizing").  
     - **Solution tease**: "Science-backed hacks to smooth transitions".  
   - Length: 150–180 chars.  

3. **Categories/Tags:**  
   - Pull from spoke’s `cluster_name` and `pillar_keywords_foundational`.  
   - Add **2–3 neuro-specific tags** (e.g., "ADHD set-shifting," "dopamine cliffs").  

4. **Keywords:**  
   - Prioritize **long-tail queries** from `search_intent_profile` (e.g., "why is switching tasks hard with ADHD").  
   - Include **community slang** (e.g., "brain freeze," "digital quicksand").  

5. **OG Image/Title:**  
   - Suggest visuals that **mirror neural conflict** (e.g., "brain gears grinding" for task-switching).  

**Example Output for `adhd-task-paralysis-focus.why-is-switching-tasks-so-mentally-painful`:**  
```markdown
---
title: "ADHD Task-Switching Pain: Why Your Brain ‘Grinds Gears’ (And How to Lubricate Them)"  
description: "That ‘mental grinding’ when switching tasks? Blame dopamine cliffs and weak inhibitory control. Discover neuro-hacks to smooth transitions and protect your focus."  
slug: "adhd-task-paralysis-focus.why-is-switching-tasks-so-mentally-painful"  
categories: ["ADHD Focus", "Executive Dysfunction", "ADHD at Work"]  
tags: ["ADHD task switching", "cognitive friction", "ADHD interruptions", "set-shifting deficit", "dopamine cliffs"]  
keywords: ["why is switching tasks painful ADHD", "ADHD brain freeze when interrupted", "how to handle task transitions ADHD", "ADHD and cognitive whiplash"]  
og_image: "/og/adhd-task-switching-pain.png"  
og_title: "ADHD Task-Switching Pain: Why Your Brain ‘Grinds Gears’"  
og_description: "Switching tasks with ADHD isn’t just hard—it’s neurologically costly. Learn why and how to reduce the friction."  
---
```

**Pro Tips for Gemini:**  
- **Inject urgency**: Use phrases like *"Science reveals why your brain rebels"* or *"Your struggle is neurobiological—here’s the workaround."*  
- **Leverage spoke’s "killer hooks"**: Borrow vivid metaphors (e.g., *"cognitive gearbox seizure"*).  
- **Align with conversion goals**: Tease the *"Operating System for ADHD Brains"* subtly (e.g., *"Your brain’s OS needs an upgrade"*).  

**Prompt for Gemini:**  
```markdown
"Generate metadata for the ADHD spoke '[INSERT-SPOKE-SLUG]' using the following rules:  
1. **Title**: Blend pain point + neuro-mechanism + solution tease. Use formats: Diagnostic/Emotional/Solution.  
2. **Description**: Hook (validate pain) + neuro-proof (cite a mechanism from the spoke’s research) + solution tease. Max 180 chars.  
3. **Categories/Tags**: Pull from spoke’s cluster/pillar keywords. Add 2 neuro-specific tags.  
4. **Keywords**: Prioritize long-tail queries and community slang from spoke’s search_intent_profile.  
5. **OG Data**: Suggest a visual metaphor for neural conflict.  

Voice: Jargon-free, empowering, and mildly rebellious (e.g., ‘Your brain isn’t broken—it’s bored’).  

Example Input: 'adhd-task-paralysis-focus.why-is-switching-tasks-so-mentally-painful'  
Example Output: [PASTE EXAMPLE ABOVE]  

Now generate for: '[INSERT-SPOKE-SLUG]'."  
"""

def discover_spoke_metadata():
    """
    Discover all spoke metadata files, extract pillar and spoke slugs, and load their JSON content.
    Returns a list of dicts: {pillar_slug, spoke_slug, metadata}
    """
    base_dir = os.path.join(os.path.dirname(__file__), SPOKE_METADATA_ROOT)
    all_spoke_entries = []
    for pillar_dir in os.listdir(base_dir):
        pillar_path = os.path.join(base_dir, pillar_dir)
        if not os.path.isdir(pillar_path):
            continue
        for fname in os.listdir(pillar_path):
            if fname.startswith("spoke-metadata.") and fname.endswith(".json"):
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
        "For a similar spoke_metadata, the following FAQ was generated:\n\n"
        f"{example_faq}\n\n"
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
    return os.path.exists(out_path)


def faq_ldjson_file_exists(pillar_slug, spoke_slug):
    out_path = os.path.join(OUTPUT_ROOT, pillar_slug, spoke_slug, "faq-ldjson.md")
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
        "For a similar spoke_metadata, the following meta section was generated:\n\n"
        f"{example_meta}\n\n"
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
    if os.path.exists(ldjson_path):
        print(f"  Skipping existing META-LDJSON for Pillar: {pillar_slug} | Spoke: {spoke_slug}")
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

