## 🧭 Blog SEO Instruction Template (For Each Post)

### ✅ STEP 1: **Clean Up the Front Matter (YAML)**

Ensure:

* **Title**: Starts with primary keyword + emotional or benefit-driven hook
* **Slug**: Matches keyword (e.g. `adhd-want-to-do-everything`)
* **Description / OG Description**: 150–160 chars, includes emotional benefit + keyword
* **OG Image Path**: Use `/og/[slug].png`
* **Tags + Keywords**: Include at least 6 keyword-rich phrases (e.g., “ADHD multiple interests”)

📌 *Keep titles, slugs, and metadata aligned.*

---

### ✅ STEP 2: **Insert an SEO-Optimized Table of Contents**

* Use anchor links (e.g., `[ADHD Energy Tips](#adhd-energy-tips)`)
* Place **after intro** and **before first H2**
* Test on mobile for visibility

---

### ✅ STEP 3: **Insert Featured Snippet Paragraph (for Google Position 0)**

* After ToC and **before first story or metaphor**
* Format as:

```markdown
## [Rephrase of Target Search Query as H2]
[40–50 word answer using clear language and keywords]
```

**Example**:

```markdown
## Why Does ADHD Make You Want to Do Everything at Once?

ADHD brains are wired for novelty and stimulation. That means new ideas, hobbies, and tasks trigger a dopamine hit — making everything feel equally urgent and exciting.
```

---

### ✅ STEP 4: **Rework All H2s to Be Keyword-Rich & Scannable**

Replace vague section headers with:

* **“What Is…”**, **“Why ADHD…”**, **“How to…”**, or emotional phrasing
* Match “People Also Ask” queries

📌 *Use a table to map current → improved headings.*

---

### ✅ STEP 5: **Rewrite FAQ Section for SEO**

* No `<details>` tags — use plain H2s and markdown
* Each question should match a real Google search phrase
* Each answer: clear, kind, ADHD-validating, with internal links
* Add rich JSON-LD `FAQPage` block at bottom of page

---

### ✅ STEP 6: **Add a Visual CTA Block for Email/Quiz Capture**

Use structure like:

```markdown
## 🎯 Ready to Channel Your ADHD Superpowers?

You're not “too much” — you’re just running on *HD high-octane brain fuel.*  
👉 **Take our Free ADHD Self-Assessment**  
[✨ Take the Quiz Now →](https://quirkylabs.ai)
```

---

### ✅ STEP 7: **Add 1–2 Visuals With Descriptive ALT Text**

* Add after intro or before big H2
* Save in `/static/images/`
* Use filenames like `adhd-brain-juggling.png`
* ALT text: “ADHD brain juggling ideas like guitar, books, and chess pieces”

---

### ✅ STEP 8: **Insert Long-Tail Keywords Strategically**

Embed keywords like:

* “ADHD overwhelmed by ideas”
* “why ADHD brain wants to start everything”
* “managing ADHD shiny object syndrome”

📍 Insert these:

* In intro paragraphs
* Inside FAQ answers
* Inside the CTA block

---

### ✅ STEP 9: **Add Breadcrumb JSON-LD Schema**

At bottom of post:

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [...]
}
```

---

### ✅ STEP 10: **Final QA Checklist**

| Area                                        | Check |
| ------------------------------------------- | ----- |
| Title includes primary keyword + hook       | ✅     |
| Description aligned and under 160 chars     | ✅     |
| Internal links to all ADHD core pages       | ✅     |
| One clear CTA to quiz or email list         | ✅     |
| JSON-LD schema: FAQ + Breadcrumb            | ✅     |
| Image(s) with alt text + filename           | ✅     |
| Emotional tone and ADHD-validating language | ✅     |
