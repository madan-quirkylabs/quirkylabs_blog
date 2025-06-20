import os
import json
from glob import glob
from core.llm_client import call_llm
from core.config import load_config

SPOKE_METADATA_ROOT = os.path.join("config", "spoke-metadata")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "output", "success")


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
    for entry in spokes:
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
    print(f"\nDone! {success_count} FAQs generated, {fail_count} failed.")

