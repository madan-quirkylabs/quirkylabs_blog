import re
import os
import json
import argparse
import logging
from core.config import load_pillar_config, load_config
from core.llm_client import call_llm
from datetime import datetime
from core.utils import extract_json_from_response

# ------------------------------
# Configurable Prompt Paths
# ------------------------------
PILLAR_PROMPT_PATH = "config/prompts/pillar_config_prompting_for_pillar.md"
SPOKE_PROMPT_PATH = "config/prompts/pillar_config_prompting_for_spoke.md"

# ------------------------------
# Output Directory
# ------------------------------
PILLAR_OUTPUT_DIR = "config/pillars"

# ------------------------------
# Utility Functions
# ------------------------------
def slugify(text):
    return text.lower().replace(" ", "-").replace("'", "").strip()

def ensure_folder(path):
    os.makedirs(path, exist_ok=True)

def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)

def read_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def extract_json_block(text):
    return extract_json_from_response(text)

# ------------------------------
# Metadata Generation Logic
# ------------------------------
def generate_pillar_metadata(pillar_slug, cluster_data, config, force=False):
    folder_path = os.path.join(PILLAR_OUTPUT_DIR, pillar_slug)
    ensure_folder(folder_path)

    pillar_json_path = os.path.join(folder_path, "pillar.json")
    if os.path.exists(pillar_json_path) and not force:
        logging.info(f"✅ Skipping pillar '{pillar_slug}' (already exists)")
        return

    prompt_template = load_prompt(PILLAR_PROMPT_PATH)
    topic = cluster_data.get("pillar_title", pillar_slug.replace("-", " "))
    spokes = cluster_data.get("spokes", [])

    # Fill in prompt
    prompt = prompt_template.replace("{{pillar_slug}}", pillar_slug)
    prompt = prompt.replace("{{pillar_title}}", topic)
    prompt = prompt.replace("{{spoke_slugs}}", json.dumps(spokes))

    logging.info(f"🔮 Generating metadata for pillar '{pillar_slug}'...")
    messages = [
        {"role": "system", "content": "You are a metadata-generating SEO agent."},
        {"role": "user", "content": prompt}
    ]
    response = call_llm(messages, section="pillar_metadata", section_config=config)
    logging.debug(f"🔍 Raw LLM response for pillar '{pillar_slug}': {repr(response)}")

    try:
        data = extract_json_block(response)
        data["prompt_version"] = "pillar-v2.1"
        write_json(pillar_json_path, data)
        logging.info(f"✅ Saved: {pillar_json_path}")
    except Exception as e:
        error_path = os.path.join(folder_path, f"pillar.{pillar_slug}.raw.txt")
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(response)
        logging.error(f"❌ Failed to parse LLM response for pillar '{pillar_slug}': {e} (raw saved to {error_path})")


def generate_spoke_metadata(spoke_slug, pillar_slug, cluster_data, config, force=False):
    folder_path = os.path.join(PILLAR_OUTPUT_DIR, pillar_slug)
    ensure_folder(folder_path)

    spoke_path = os.path.join(folder_path, f"spoke.{spoke_slug}.json")
    if os.path.exists(spoke_path) and not force:
        logging.info(f"✅ Skipping spoke '{spoke_slug}' (already exists)")
        return

    prompt_template = load_prompt(SPOKE_PROMPT_PATH)
    pillar_title = cluster_data.get("pillar_title", pillar_slug.replace("-", " "))

    # Fill in prompt
    prompt = prompt_template.replace("{{spoke_slug}}", spoke_slug)
    prompt = prompt.replace("{{pillar_slug}}", pillar_slug)
    prompt = prompt.replace("{{pillar_title}}", pillar_title)

    logging.info(f"🧠 Generating metadata for spoke '{spoke_slug}'...")
    messages = [
        {"role": "system", "content": "You are a metadata-generating SEO agent for ADHD blogs."},
        {"role": "user", "content": prompt}
    ]
    response = call_llm(messages, section="spoke_metadata", section_config=config)
    logging.debug(f"🔍 Raw LLM response for spoke '{spoke_slug}': {repr(response)}")

    try:
        data = extract_json_block(response)
        data["prompt_version"] = "spoke-v3.1"
        write_json(spoke_path, data)
        logging.info(f"✅ Saved: {spoke_path}")
    except Exception as e:
        error_path = os.path.join(folder_path, f"spoke.{spoke_slug}.raw.txt")
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(response)
        logging.error(f"❌ Failed to parse LLM response for spoke '{spoke_slug}': {e} (raw saved to {error_path})")

# ------------------------------
# Main Entry Point
# ------------------------------
def main(force=False, pillar_only=False, spoke_only=False, target_pillar=None):
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(levelname)s - %(message)s")
    logging.info("🚀 Starting metadata generation pipeline...")

    pillar_config = load_pillar_config()
    config = load_config()

    logging.info(f"🌐 Using LLM provider: {config.get('llm_provider')} model: {config.get(config['llm_provider'], {}).get('model')}")

    for pillar_slug, cluster_data in pillar_config.items():
        if target_pillar and pillar_slug != target_pillar:
            continue

        if not spoke_only:
            generate_pillar_metadata(pillar_slug, cluster_data, config=config, force=force)

        if not pillar_only:
            for spoke_slug in cluster_data.get("spokes", []):
                generate_spoke_metadata(spoke_slug, pillar_slug, cluster_data, config=config, force=force)

    logging.info("🏁 All metadata generation completed.")

# ------------------------------
# CLI Argument Parser
# ------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate LLM metadata for ADHD pillar+spoke SEO structure.")
    parser.add_argument("--force", action="store_true", help="Force regenerate files even if they exist")
    parser.add_argument("--pillar-only", action="store_true", help="Generate only pillar metadata")
    parser.add_argument("--spoke-only", action="store_true", help="Generate only spoke metadata")
    parser.add_argument("--target", type=str, help="Only generate metadata for a single pillar_slug")
    args = parser.parse_args()

    main(force=args.force, pillar_only=args.pillar_only, spoke_only=args.spoke_only, target_pillar=args.target)
