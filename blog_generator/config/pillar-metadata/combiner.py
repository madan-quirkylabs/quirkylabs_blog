import json
from pathlib import Path

# --- CONFIG --------------------------------------------------------
FOLDER = Path(r"C:\Users\madan\MyProjects\quirkly-labs-code\quirkylabs_blog\blog_generator\config\pillar-metadata")  # change this
OUTPUT_FILE = FOLDER / "combined.json"
# -------------------------------------------------------------------

def main():
    combined: dict[str, object] = {}

    for file_path in FOLDER.glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                combined[file_path.name] = json.load(f)
        except json.JSONDecodeError as e:
            # Skip files that aren't valid JSON
            print(f"Skipping {file_path.name}: {e}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        json.dump(combined, out, ensure_ascii=False, indent=2)

    print(f"✔ Combined {len(combined)} files into {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
