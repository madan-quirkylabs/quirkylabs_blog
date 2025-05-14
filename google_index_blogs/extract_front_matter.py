import os
import yaml
import csv

def extract_front_matter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if lines[0].strip() != '---':
        return None

    front_matter = []
    for line in lines[1:]:
        if line.strip() == '---':
            break
        front_matter.append(line)

    return yaml.safe_load(''.join(front_matter))

def process_files(directory):
    data = []
    for filename in os.listdir(directory):
        if filename.startswith("adhd") and filename.endswith(".md"):
            filepath = os.path.join(directory, filename)
            front_matter = extract_front_matter(filepath)
            if front_matter:
                data.append({
                    "filename": filename,
                    "title": front_matter.get("title", ""),
                    "description": front_matter.get("description", ""),
                    "slug": front_matter.get("slug", ""),
                    "date": front_matter.get("date", ""),
                    "categories": ', '.join(front_matter.get("categories", [])),
                    "tags": ', '.join(front_matter.get("tags", [])),
                    "keywords": ', '.join(front_matter.get("keywords", [])),
                })

    with open("adhd_blogs_export.csv", "w", newline='', encoding='utf-8') as csvfile:
        fieldnames = ["filename", "title", "description", "slug", "date", "categories", "tags", "keywords"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in data:
            writer.writerow(entry)

    print(f"Exported {len(data)} files to adhd_blogs_export.csv")

# Example usage
process_files("../content/pages/")
