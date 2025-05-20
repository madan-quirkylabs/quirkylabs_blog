# scripts/generate_narrative_blogs.py

import os
import sys
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

# Load sample input CSV
def load_generation_targets():
    df = pd.read_csv(os.path.join(INPUT_DIR, "sample_input.csv"))
    df.columns = df.columns.str.strip().str.lower()
    return df.to_dict(orient="records")

# Load pillar config to verify paths (optional)
def load_metadata_for(pillar_slug, spoke_slug):
    path = f"config/pillars/{pillar_slug}/spoke.{spoke_slug}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_study(study):
    citation = study.get("citation", "")
    mechanism = study.get("neurobiological_mechanism", "")
    return f"{mechanism} (Source: {citation})"

def generate_full_prompt(meta):
    prompt = narrative_prompt_cfg["prompt"]
    filled = prompt.replace("{{titles.diagnostic}}", meta["titles"]["diagnostic"])

    # Fill dynamic metadata
    hook = meta.get("hook", "")
    core_pain_point = meta.get("core_pain_point", "")
    meme_grenade = meta["content_ops"]["internal_links"][0]["meme_grenade"]
    voice = meta.get("voice_combat", [])
    reddit = meta.get("reddit_slang", [])
    paa = meta["serp_warfare"]["paa_nesting"]
    conversion = meta["conversion_nuke"]
    checklist = conversion.get("quiz", {}).get("questions", ["..."])
    visual_breakers = meta["content_ops"].get("visual_breakers", ["💥"])

    # Insert structured elements
    filled = filled.replace("{{core_pain_point}}", core_pain_point)
    filled = filled.replace("{{meme_grenade}}", meme_grenade)
    filled = filled.replace("{{hook.split('PS:')[1]}}", hook.split("PS:")[-1].strip())
    filled = filled.replace("{{voice_combat[0]}}", voice[0] if voice else "How do I survive this?")
    filled = filled.replace("{{reddit_slang[0]}}", reddit[0] if reddit else "chaos loop")
    filled = filled.replace("{{real_study_citation_inputs[0].neurobiological_mechanism}}", format_study(meta["real_study_citation_inputs"][0]))
    filled = filled.replace("{{conversion_nuke.dopamine_trigger.split('→')[1]}}", conversion.get("dopamine_trigger", "→ Do something").split("→")[-1].strip())
    filled = filled.replace("{{titles.solution}}", meta["titles"]["solution"])
    filled = filled.replace("{{paa_nesting[0]}}", paa[0] if paa else "Why does this happen?")
    filled = filled.replace("{{conversion_nuke.quiz.name}}", conversion.get("quiz", {}).get("name", "What's your meltdown style?"))
    filled = filled.replace("{{checklist.questions[0]}}", checklist[0])
    filled = filled.replace("{{conversion_nuke.hook}}", conversion.get("hook", "You’ll regret not downloading this."))
    filled = filled.replace("{{lead_magnet}}", conversion.get("lead_magnet", "ADHD Rescue Kit"))
    filled = filled.replace("{{downloadable_bonus}}", conversion.get("downloadable_bonus", "Bonus PDF"))

    return filled

def extract_sections(text):
    pattern = r"<!--START: (.*?)-->\n(.*?)<!--END: \\1-->"
    matches = re.findall(pattern, text, re.DOTALL)
    return {section.strip(): content.strip() for section, content in matches}

def main():
    ensure_directories({"output": SUCCESS_DIR, "logs": LOGS_DIR})
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
            full_prompt = generate_full_prompt(meta)
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
            with open(os.path.join(LOGS_DIR, f"{slug}.full.md"), "w", encoding="utf-8") as f:
                f.write(response)

            print(f"✅ Blog '{slug}' saved with {len(sections)} sections.")

        except Exception as e:
            print(f"❌ Error processing {slug}: {e}")

if __name__ == "__main__":
    main()
