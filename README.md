# 🧠 Resume Forge

**Resume Forge** is a powerful, AI-assisted resume generator that tailors your resume for specific job descriptions — particularly tech roles — using GPT-4o, HTML/CSS templating, and automation tooling like Playwright.

## ✨ Features

- 🔍 **Job Description Parsing** — Automatically extracts top responsibilities, keywords, and the advertised role/company from a LinkedIn job URL.
- 🧠 **AI-Tailored Work Experience** — Uses GPT-4o to rewrite your experience using resume best practices (APR format).
- 🧰 **Skill Filtering + Suggestions** — Identifies relevant skills and suggests new ones from the job description.
- 📝 **Professional Summary Generation** — Generates a tailored summary aligned to the target role.
- 🎨 **HTML-to-PDF Rendering** — Produces clean, ATS-friendly PDFs from HTML/CSS templates using Playwright.
- ⚙️ **Configurable Settings** — Toggle pruning, relevance-based sorting, and project visibility via `settings.yaml`.
- 🧪 **Dev Mode** — Save and reload resume data to preview layout without rerunning GPT.

---

## 📁 File Structure
```bash
Resume-Forge/
│
├── data/
│   └── resume.yaml              # All resume content (experience, skills, education, contact info)
│
├── output/
│   ├── resume.pdf               # Final rendered resume
│   └── sample_resume.json       # JSON version of resume data for testing
│
├── templates/
│   └── classic_resume/          # HTML + CSS for resume layout
│       └── template.html
│
├── .env                         # Contains your OpenAI API key
├── resume_generator.py          # Main pipeline script
├── settings.yaml                # Config flags (e.g., prune_irrelevant, prioritize_relevance)
└── README.md                    # You’re here!
```

## ⚙️ Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create .env file
```bash
OPENAI_API_KEY=your-openai-key
```

### 3. Prepare your resume content
Edit `data/resume.yaml` with your name, contact info, education, skills, and full work history. This is your "master resume" that gets tailored.

### 4. Configure optional settings (optional)

Edit the `data/settings.yaml` file to control resume behavior:

```yaml
prune_irrelevant: true       # If true, GPT may exclude jobs unrelated to the role (while keeping at least 3)
prioritize_relevance: true   # Reorders experience based on relevance rather than strict chronology
include_projects: true       # Includes personal projects in the final resume if available
```

---

## 🚀 Usage

### 🔄 Generate a tailored resume

```bash
python resume_generator.py
```

You’ll be prompted to paste a LinkedIn job URL. GPT-4o will handle everything: analyzing the job, extracting responsibilities and keywords, filtering your skills, tailoring your experience, and generating a customized PDF resume.

- 📌 If GPT suggests new skills and you choose to include them, they will be automatically added to your `resume.yaml` for future use.
- 📄 The output file will be saved as a PDF using the format: `firstname_lastname_company_jobtitle.pdf`

### 🛠 Preview resume layout without GPT calls

```bash
python render_preview.py
```

This renders the resume using the last saved `output/sample_resume.json`. Great for template debugging.

---

## 💡 Tips

- 🧠 GPT will not invent missing data — make sure your `resume.yaml` is complete.
- 🎨 Edit `template.html` and `style.css` to fully customize your resume's visual style.
- 🔁 Use `render_preview.py` to test layout changes without re-running GPT.
- 📂 Check the `output/` folder for your final and intermediate files.

---

## 🧑‍💻 Example YAML Snippet

```yaml
name: Jane Doe
contact:
  email: jane.doe@example.com
  phone: 555-123-4567
  location: San Francisco, CA
  linkedin: www.linkedin.com/in/janedoe
  github: https://github.com/janedoe

education:
  - degree: Master of Science, Computer Science
    school: Stanford University
  - degree: Bachelor of Science, Computer Engineering
    school: University of California, Berkeley

skills:
  - JavaScript
  - React
  - Node.js
  - Flask
  - Django
  - AWS
  - GCP
```

---

## 📄 License

MIT License — free for personal and commercial use.

---

## 🤝 Contributions

Feature ideas and PRs are welcome! Submit a GitHub issue if you’d like to contribute or request improvements.

---

## 🧠 Powered By

- [OpenAI GPT-4o](https://openai.com/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [Playwright](https://playwright.dev/)
- [YAML](https://yaml.org/)