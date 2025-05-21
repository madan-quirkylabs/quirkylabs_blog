# scripts/generate_narrative_blogs.py

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import yaml
import json
import re
import textstat
import pandas as pd
from datetime import datetime
from core.config import INPUT_DIR, SUCCESS_DIR, LOGS_DIR, SECTION_PROMPTS_PATH
from core.utils import save_section, ensure_directories, extract_yaml_from_response, extract_json_from_response
from core.llm_client import call_llm

# Load prompts
with open(SECTION_PROMPTS_PATH, "r", encoding="utf-8") as f:
    prompts_dict = yaml.safe_load(f)

narrative_prompt_cfg = prompts_dict["narrative_full_blog"]
front_matter_prompt_cfg = prompts_dict["narrative_blog_front_matter"]
narrative_seo_heading_cfg = prompts_dict["narrative_seo_headings"]
narrative_faq_section_cfg = prompts_dict["narrative_faq_section"]

# Load generation targets from sample_input.csv
def load_generation_targets():
    df = pd.read_csv(os.path.join(INPUT_DIR, "sample_input.csv"))
    df.columns = df.columns.str.strip().str.lower()
    return df.to_dict(orient="records")

# Load specific spoke metadata given pillar + spoke slug
def load_metadata_for(pillar_slug, spoke_slug):
    path = f"config/pillars/{pillar_slug}/spoke.{spoke_slug}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_study(study):
    citation = study.get("citation", "")
    mechanism = study.get("neurobiological_mechanism", "")
    return f"{mechanism} (Source: {citation})"

def generate_full_prompt(meta, prompt_template):
    prompt = prompt_template
    filled = prompt.replace("{{titles.diagnostic}}", meta["titles"]["diagnostic"])

    hook = meta.get("hook", "")
    core_pain_point = meta["spoke_metadata_inputs"].get("core_pain_point", "").strip().capitalize()
    filled = filled.replace("{{core_pain_point}}", core_pain_point)
    filled = filled.replace("{{hook.split('PS:')[1]}}", meta["hook"].split("PS:")[1].split("→")[0].strip())

    primary_keyword = next(
            (kw for kw in meta["spoke_metadata_inputs"]["pillar_keywords"] 
             if kw not in ["can't", "my", "overwhelm", "stop"]),
            meta["spoke_metadata_inputs"]["pillar_keywords"][0]
        )
    filled = filled.replace("{{primary_keyword}}", primary_keyword)
    filled = filled.replace("{{slug}}", meta["spoke_name"])


    # Fill simple metadata values
    filled = filled.replace("{{titles.solution}}", meta["titles"].get("solution", "Fix your ADHD brain"))
    conversion = meta.get("conversion_nuke", {})
    filled = filled.replace("{{conversion_nuke.hook}}", conversion.get("hook", "Click now or the moment is gone."))
    filled = filled.replace("{{conversion_nuke.quiz.name}}", f"{meta['conversion_nuke']['schema']['Quiz']['name']} ({meta['conversion_nuke']['schema']['Quiz']['dopamine_trigger']})")
    filled = filled.replace("{{lead_magnet}}", conversion.get("lead_magnet", "Breakup Survival Kit"))
    filled = filled.replace("{{downloadable_bonus}}", conversion.get("downloadable_bonus", "Cheat Sheet PDF"))
    filled = filled.replace("{{conversion_nuke.dopamine_trigger.split('→')[1]}}", conversion.get("dopamine_trigger", "→ Reward loop hack").split("→")[-1].strip())

    voice_search = next(
            (vs for vs in meta["spoke_metadata_inputs"]["voice_search"] 
            if vs.startswith(("why", "how", "what"))),
            meta["spoke_metadata_inputs"]["voice_search"][0]
        ).replace("Hey Google, ", "")
    filled = filled.replace("{{voice_search}}", voice_search)

    # Insert meme_grenade
    meme_grenade = meta["content_ops"]["pillar_sync"]["internal_links"][0].get("meme_grenade", "your brain is just a drama queen")
    filled = filled.replace("{{meme_grenade}}", meme_grenade)

    # Insert study_grenade and neuro_nugget
    study_grenade = meta["serp_warfare"]["study_grenade"].replace("“", "").replace("”", "").split("–")[0].strip()
    filled = filled.replace("{{study_grenade}}", study_grenade)
    studies = meta.get("real_study_citation_inputs", [])
    if len(studies) > 1:
        nugget = studies[1].get("top_3_findings", ["ADHD makes emotional regulation volatile."])[0]
    elif studies:
        nugget = studies[0].get("top_3_findings", ["ADHD makes emotional regulation volatile."])[0]
    else:
        nugget = "Emotional chaos is real with ADHD."
    filled = filled.replace("{{neuro_nugget}}", nugget)

    # Replace list elements by indexed placeholders
    for i, q in enumerate(conversion.get("quiz", {}).get("questions", [])):
        filled = filled.replace(f"{{{{checklist.questions[{i}]}}}}", q)

    for i, v in enumerate(meta.get("voice_combat", [])):
        filled = filled.replace(f"{{{{voice_combat[{i}]}}}}", v)

    reddit_slang_list = json.dumps(meta["spoke_metadata_inputs"].get("reddit_slang", []), indent=2)
    filled.replace("{{reddit_slang}}", reddit_slang_list)
    for i, r in enumerate(meta["spoke_metadata_inputs"].get("reddit_slang", [])):
        filled = filled.replace(f"{{{{reddit_slang[{i}]}}}}", r)

    for i, p in enumerate(meta.get("serp_warfare", {}).get("paa_nesting", [])):
        filled = filled.replace(f"{{{{paa_nesting[{i}]}}}}", p)

    for i, vb in enumerate(meta["content_ops"]["pillar_sync"].get("visual_breakers", [])):
        filled = filled.replace(f"{{{{visual_breakers[{i}]}}}}", vb)

    for i, s in enumerate(meta.get("real_study_citation_inputs", [])):
        summary = s.get("neurobiological_mechanism", "ADHD causes emotional spikes.")
        filled = filled.replace(f"{{{{real_study_citation_inputs[{i}].neurobiological_mechanism}}}}", format_study(s))

    return filled

def generate_front_matter(meta):
    slug = meta["spoke_name"]
    prompt_template = front_matter_prompt_cfg["prompt"]
    full_prompt = generate_full_prompt(meta, prompt_template)
    system_instruction = front_matter_prompt_cfg["system_instruction"]
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": full_prompt}
    ]
    if not front_matter_prompt_cfg.get("enabled", True):
        print(f"⚠️ Skipping generation of front-matter for '{slug}' because it is disabled in section_prompts.yaml")
        return

    provider = front_matter_prompt_cfg.get("provider", "openai")
    model = front_matter_prompt_cfg.get("model")
    temperature = front_matter_prompt_cfg.get("temperature")
    front_matter = call_llm(
        messages,
        section="narrative_blog_front_matter",
        section_config=front_matter_prompt_cfg,
        provider=provider,
        model=model,
        temperature=temperature
    )

    front_matter = extract_yaml_from_response(front_matter)

    try:
        if front_matter:
            front_matter_path = os.path.join(SUCCESS_DIR, slug, "front_matter.yaml")
            os.makedirs(os.path.dirname(front_matter_path), exist_ok=True)
            with open(front_matter_path, "w", encoding="utf-8") as f:
                f.write(front_matter.strip() + "\n")
            print(f"✅ Front matter saved to {front_matter_path}")
        else:
            print(f"⚠️ No front matter returned for {slug}")
    except Exception as e:
        print(f"❌ Failed to generate/save front matter for {slug}: {e}")


    return front_matter

def extract_sections(text):
    pattern = r"<!--START: (.*?)-->\n(.*?)<!--END: \\1-->"
    matches = re.findall(pattern, text, re.DOTALL)
    return {section.strip(): content.strip() for section, content in matches}

def generate_narrative_blog(meta):
    slug = meta["spoke_name"]
    prompt_template = narrative_prompt_cfg["prompt"]
    full_prompt = generate_full_prompt(meta, prompt_template)
    messages = [
        {"role": "system", "content": narrative_prompt_cfg["system_instruction"]},
        {"role": "user", "content": full_prompt}
    ]

    if not narrative_prompt_cfg.get("enabled", True):
        print(f"⚠️ Skipping generation for '{slug}' because it is disabled in section_prompts.yaml")
        return

    provider = narrative_prompt_cfg.get("provider", "openai")
    model = narrative_prompt_cfg.get("model")
    temperature = narrative_prompt_cfg.get("temperature")

    response = call_llm(
        messages,
        section="narrative_full_blog",
        section_config=narrative_prompt_cfg,
        provider=provider,
        model=model,
        temperature=temperature
    )

    sections = extract_sections(response)

    for name, content in sections.items():
        save_section(slug, name, content)

    narrative_path = os.path.join(SUCCESS_DIR, slug, "narrative_blog.md")
    os.makedirs(os.path.dirname(narrative_path), exist_ok=True)
    with open(narrative_path, "w", encoding="utf-8") as f:
        f.write(response)

    print(f"✅ Blog '{slug}' saved with {len(sections)} sections.")

def generate_seo_headings(meta):
    slug = meta["spoke_name"]
    prompt_template = narrative_seo_heading_cfg["prompt"]
    full_prompt = generate_full_prompt(meta, prompt_template)
    
    messages = [
        {"role": "system", "content": narrative_seo_heading_cfg["system_instruction"]},
        {"role": "user", "content": full_prompt}
    ]

    if not narrative_seo_heading_cfg.get("enabled", True):
        print(f"⚠️ Skipping generation of seo_headings for '{slug}' because it is disabled in section_prompts.yaml")
        return
    
    response = call_llm(
        messages,
        section="narrative_seo_headings",
        section_config=narrative_seo_heading_cfg,
        provider=narrative_seo_heading_cfg.get("provider"),
        model=narrative_seo_heading_cfg.get("model"),
        temperature=narrative_seo_heading_cfg.get("temperature")
    )
    
    headings_path = os.path.join(SUCCESS_DIR, slug, "narrative_seo_headings.md")
    with open(headings_path, "w", encoding="utf-8") as f:
        f.write(response)
    
    return response

def generate_faq_section(meta):
    slug = meta["spoke_name"]
    prompt_template = narrative_faq_section_cfg["prompt"]

    if not narrative_faq_section_cfg.get("enabled", True):
        print(f"⚠️ Skipping generation of FAQ for '{slug}' because it is disabled in section_prompts.yaml")
        return
    
    # Format studies for prompt
    studies_text = "\n".join([
        f"- {s['citation']}: {s['top_3_findings'][0]}"
        for s in meta.get("real_study_citation_inputs", [])[:3]
    ])
    
    full_prompt = prompt_template\
        .replace("{{topic}}", meta["spoke_metadata_inputs"].get("core_pain_point", ""))\
        .replace("{{primary_keyword}}", next(
            (kw for kw in meta["spoke_metadata_inputs"]["pillar_keywords"] 
             if kw not in ["can't", "my", "overwhelm", "stop"]),
            meta["spoke_metadata_inputs"]["pillar_keywords"][0]
        ))\
        .replace("{{real_study_citation_inputs}}", studies_text)
    
    messages = [
        {"role": "system", "content": narrative_faq_section_cfg["system_instruction"]},
        {"role": "user", "content": full_prompt}
    ]
    
    response = call_llm(
        messages,
        section="narrative_faq_section",
        section_config=narrative_faq_section_cfg,
        provider=narrative_faq_section_cfg.get("provider"),
        model=narrative_faq_section_cfg.get("model"),
        temperature=narrative_faq_section_cfg.get("temperature")
    )

    json_result = extract_json_from_response(response)
    
    faq_path = os.path.join(SUCCESS_DIR, slug, "narrative_faq_section.json")
    with open(faq_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(json_result, indent=2))
    
    return json_result

def main():
    ensure_directories({"output": SUCCESS_DIR, "logs": LOGS_DIR})
    os.makedirs(SUCCESS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    targets = load_generation_targets()

    for row in targets:
        pillar_slug = row["pillar_slug"]
        spoke_slug = row["spoke_slug"]

        try:
            meta = load_metadata_for(pillar_slug, spoke_slug)
        except Exception as e:
            print(f"❌ Skipping {spoke_slug} – couldn’t load metadata: {e}")
            continue

        slug = meta["spoke_name"]
        print(f"\n🚀 Generating: {slug} (from {pillar_slug})")

        # ✅ Call front matter generator
        try:
            generate_front_matter(meta)
        except Exception as e:
            print(f"❌ Front matter generation failed for {slug}: {e}")

        try:
            generate_narrative_blog(meta)
        except Exception as e:
            print(f"❌ Error processing narrative blog {slug}: {e}")

        try:
            generate_seo_headings(meta)
        except Exception as e:
            print(f"❌ Error processing narrative blog {slug}: {e}")

        try:
            generate_faq_section(meta)
        except Exception as e:
            print(f"❌ Error processing narrative blog {slug}: {e}")

if __name__ == "__main__":
    main()
