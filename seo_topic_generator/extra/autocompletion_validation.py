import json
from difflib import SequenceMatcher

# === STEP 1: Define your fear-based pillars ===
fear_pillars = {
    "will-i-ever-get-my-life-together": "Will I Ever Get My Life Together?",
    "hidden-life-of-adhd-impostors": "The Hidden Life of ADHD Impostors",
    "rest-feels-unsafe-adhd-hustle": "Rest Feels Unsafe: The ADHD Hustle Curse",
    "adhd-lonely-mind": "The Loneliness of the ADHD Mind",
    "adhd-dreams-vs-discipline": "ADHD Dreams vs. ADHD Discipline",
    "living-under-label": "Living Under the Label: Stupid, Lazy, or Just ADHD?",
    "adhd-fear-of-being-unlovable": "ADHD and the Fear of Being Unlovable"
}

# === STEP 2: Load your autocomplete JSON ===
AUTOCOMPLETE_FILE = "autocomplete_data.json"

try:
    with open(AUTOCOMPLETE_FILE, "r", encoding="utf-8") as f:
        autocomplete_data = json.load(f)
except FileNotFoundError:
    print(f"❌ Could not find file: {AUTOCOMPLETE_FILE}")
    exit(1)

# === STEP 3: Helper for fuzzy string comparison ===
def is_similar(a, b, threshold=0.6):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold

# === STEP 4: Match pillars to autocomplete suggestions ===
results = {}

for slug, title in fear_pillars.items():
    title_words = [w for w in title.lower().split() if len(w) > 3]
    matches = []

    for seed, suggestions in autocomplete_data.items():
        for suggestion in suggestions:
            suggestion_lower = suggestion.lower()
            if any(word in suggestion_lower for word in title_words) or is_similar(suggestion, title):
                matches.append(suggestion)

    results[slug] = {
        "title": title,
        "matches_found": sorted(list(set(matches))),
        "is_validated": len(matches) > 0
    }

# === STEP 5: Output the result ===
output_file = "validated_pillars.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"✅ Validation complete. Results saved to: {output_file}")
