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
from core.utils import save_section, ensure_directories
from core.llm_client import call_llm

# Load prompts
with open(SECTION_PROMPTS_PATH, "r", encoding="utf-8") as f:
    prompts_dict = yaml.safe_load(f)

narrative_prompt_cfg = prompts_dict["narrative_full_blog"]

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
    core_pain_point = meta.get("core_pain_point", "")
    filled = filled.replace("{{core_pain_point}}", core_pain_point)
    filled = filled.replace("{{hook.split('PS:')[1]}}", hook.split("PS:")[-1].strip())

    # Fill simple metadata values
    filled = filled.replace("{{titles.solution}}", meta["titles"].get("solution", "Fix your ADHD brain"))
    conversion = meta.get("conversion_nuke", {})
    filled = filled.replace("{{conversion_nuke.hook}}", conversion.get("hook", "Click now or the moment is gone."))
    filled = filled.replace("{{conversion_nuke.quiz.name}}", conversion.get("quiz", {}).get("name", "What's your ADHD breakup style?"))
    filled = filled.replace("{{lead_magnet}}", conversion.get("lead_magnet", "Breakup Survival Kit"))
    filled = filled.replace("{{downloadable_bonus}}", conversion.get("downloadable_bonus", "Cheat Sheet PDF"))
    filled = filled.replace("{{conversion_nuke.dopamine_trigger.split('→')[1]}}", conversion.get("dopamine_trigger", "→ Reward loop hack").split("→")[-1].strip())

    # Insert meme_grenade
    meme_grenade = meta["content_ops"]["pillar_sync"]["internal_links"][0].get("meme_grenade", "your brain is just a drama queen")
    filled = filled.replace("{{meme_grenade}}", meme_grenade)

    # Insert study_grenade and neuro_nugget
    study_grenade = meta["serp_warfare"].get("study_grenade", "ADHD brains confuse love withdrawal with physical pain.")
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

    for i, r in enumerate(meta.get("reddit_slang", [])):
        filled = filled.replace(f"{{{{reddit_slang[{i}]}}}}", r)

    for i, p in enumerate(meta.get("serp_warfare", {}).get("paa_nesting", [])):
        filled = filled.replace(f"{{{{paa_nesting[{i}]}}}}", p)

    for i, vb in enumerate(meta["content_ops"].get("visual_breakers", [])):
        filled = filled.replace(f"{{{{visual_breakers[{i}]}}}}", vb)

    for i, s in enumerate(meta.get("real_study_citation_inputs", [])):
        summary = s.get("neurobiological_mechanism", "ADHD causes emotional spikes.")
        filled = filled.replace(f"{{{{real_study_citation_inputs[{i}].neurobiological_mechanism}}}}", format_study(s))

    return filled

def extract_sections(text):
    pattern = r"<!--START: (.*?)-->\n(.*?)<!--END: \\1-->"
    matches = re.findall(pattern, text, re.DOTALL)
    return {section.strip(): content.strip() for section, content in matches}

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

        try:
            prompt_template = narrative_prompt_cfg["prompt"]
            full_prompt = generate_full_prompt(meta, prompt_template)
            messages = [
                {"role": "system", "content": narrative_prompt_cfg["system_instruction"]},
                {"role": "user", "content": full_prompt}
            ]

            if not narrative_prompt_cfg.get("enabled", True):
                print(f"⚠️ Skipping generation for '{slug}' because it is disabled in section_prompts.yaml")
                continue

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

            # Save full response for debug
            log_path = os.path.join(LOGS_DIR, f"{slug}.full.md")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(response)

            print(f"✅ Blog '{slug}' saved with {len(sections)} sections.")

        except Exception as e:
            print(f"❌ Error processing {slug}: {e}")

if __name__ == "__main__":
    main()
