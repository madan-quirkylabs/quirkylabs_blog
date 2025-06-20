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

