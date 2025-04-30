## -----------------------------------------------------
# What works for now
# Run the parallel_generate_landing_pages.py directly using python.
# Feed the sameple_input.csv as its input file
# Rest doesn't work
## -----------------------------------------------------


# 🚀 QuirkyLabs Blog Generation System

Welcome to the **QuirkyLabs Blog Generator** — a modular, human-first, SEO-optimized blog generation engine for ADHD-related content.

---

## 📂 Project Structure

| File/Folder | Purpose |
|:---|:---|
| `parallel_generate_landing_pages.py` | Main script to generate blogs in parallel section-by-section and blog-by-blog. |
| `sample_input.csv` | List of topics and keywords to generate blogs for. |
| `quirkylabs_section_prompts.json` | Dynamic prompts used to generate each blog section and validate outputs. Strict metaphor control now relaxed for better human readability. |
| `quirky_landing_page_system.md` | Governs overall blog structure and checklist standards. |
| `master_landing_page_creation_prompt.md` | Governs tone, emotionality, and human writing style guidelines. |
| `.env` | Safely stores your OpenAI API Key. |
| `/output/` | Folder where final `.md` blogs are saved. |

---

## 🛠 Setup Instructions

1. Clone the repo / set up locally.
2. Install Python packages:

```bash
pip install openai python-dotenv textstat


