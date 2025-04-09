from dotenv import load_dotenv
import json
import os
import requests
import yaml
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from playwright.sync_api import sync_playwright

def estimate_word_count(text):
    return len(text.split())

def compute_work_experience_budget(summary, skills, education, projects, total_limit=600):
    summary_words = estimate_word_count(summary)
    # print("-----------------------")
    # print(f"summary word count: {summary_words}")
    skill_words = len(" ".join(skills).split())
    # print(f"skill word count: {skill_words}")
    edu_words = sum(len(e['degree'].split()) + len(e['school'].split()) for e in education)
    # print(f"education word count: {edu_words}")
    # Prefer tailored_projects if available
    if projects:
        if isinstance(projects, list) and all("description" in p for p in projects):
            proj_words = sum(len(p["title"].split()) + len(p["description"].split()) for p in projects)
        else:
            proj_words = sum(len(p.get("title", "").split()) + len(p.get("description", "").split()) for p in projects)
    else:
        proj_words = 0
    # print(f"proj_words word count: {proj_words}")

    used = summary_words + skill_words + edu_words + proj_words
    # print(f"total word count: {used}")
    remaining = total_limit - used
    # print(f"remaining word count: {remaining}")
    # print(f"Budget: {max(300, min(remaining, 450))}")
    return max(300, min(remaining, 450))  # Clamp budget to 300–450

# Load environment variables from .env file
load_dotenv()

# Load settings from settings.yaml
def load_settings(path="data/settings.yaml"):
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"[WARNING] The settings file {path} was not found. Using defaults.")
        return {}
    except yaml.YAMLError as e:
        print(f"[ERROR] Failed to parse settings YAML: {e}")
        raise

settings = load_settings()
prune_irrelevant = settings.get("prune_irrelevant", False)
prioritize_relevance = settings.get("prioritize_relevance", False)
include_projects = settings.get("include_projects", False)

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def format_date(date_str):
    """Format a date string from 'YYYY-MM' to 'MMM. YYYY'."""
    try:
        return datetime.strptime(date_str, "%Y-%m").strftime("%b. %Y")
    except Exception:
        return date_str

def strip_json_codeblock(text):
    """Remove code block formatting from the provided text."""
    lines = text.strip().splitlines()
    lines = [line for line in lines if not line.strip().lower().startswith("```") and line.strip().lower() != "json"]
    return "\n".join(lines).strip()

def load_resume(path="data/resume.yaml"):
    """Load resume data from a YAML file."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"[ERROR] The file {path} was not found.")
        raise
    except yaml.YAMLError as e:
        print(f"[ERROR] Failed to parse YAML file: {e}")
        raise

def fetch_job_description(linkedin_url):
    """Fetch job description from LinkedIn URL."""
    try:
        response = requests.get(linkedin_url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch job description: {e}")
        raise

def extract_top_responsibilities(job_description):
    prompt = f"""
    From the job description below:
    1. Identify and briefly describe the 3 most important responsibilities a successful candidate must demonstrate.
    2. Extract a list of up to 20 key skills, technologies, and keywords mentioned by name in the job description.
    3. Identify the job title and company name the description is advertising.
    4. Provide a 1–2 sentence summary of the job description that highlights its focus and context.

    Return ONLY valid JSON in the exact format below. Do not include commentary, explanations, markdown, or headings. Do not wrap the output in code blocks. Output must begin with a {{ and end with a }}.

    {{
    "responsibilities": [
        "Responsibility 1",
        "Responsibility 2",
        "Responsibility 3"
    ],
    "keywords": [
        "Keyword 1", "Keyword 2", "Keyword 3"
    ],
    "target_job_title": "Job Title",
    "target_company": "Company Name",
    "job_summary": "A concise summary of the job’s key themes and requirements."
    }}

    Job Description:
    {job_description}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert resume writer with 20+ years of experience helping professionals break into the tech industry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        output = response.choices[0].message.content.strip()
        output = strip_json_codeblock(output)
        return json.loads(output)
    except json.JSONDecodeError as e:
        print("[ERROR] Failed to parse GPT output.")
        raise e
    except Exception as e:
        print(f"[ERROR] An error occurred while extracting responsibilities: {e}")
        raise

def tailor_work_experience(experience, job_summary, responsibilities, keywords, role, company, max_words, prune_irrelevant=False, prioritize_relevance=False):
    """Tailor work experience to align with job responsibilities and keywords."""
    prompt = f"""
    Based on the 3 key responsibilities below, tailor the following resume work experience section to better align with a {role} position at {company}.

    - Use only the real content provided.
    - Do NOT fabricate accomplishments.
    - Use Action + Project/Problem + Result (APR) format where appropriate, emphasizing numeric value.
    - Naturally include relevant keywords from the job description.
    - 3 - 6 bullets per job
    {"- You may remove experiences that are clearly unrelated to the role. However, keep at least 3 jobs if 3 or more are provided." if prune_irrelevant else "- Do not remove any jobs, even if they are unrelated."}
    {"- Organize the work experience by relevance to the job rather than chronological order." if prioritize_relevance else "- Maintain chronological ordering of job experience."}
    - The total length of "bullets" content across "work_experience" should be approximately {max_words} words. This is extremely important. More recent experience should have more content.

    Return ONLY valid JSON in the exact format below. Do not include commentary, explanations, markdown, or headings. Do not wrap the output in code blocks. Output must begin with a {{ and end with a }}.

    Format:
    {{
      "work_experience": [
        {{
          "title": "Job Title",
          "company": "Company Name",
          "start_date": "YYYY-MM",
          "end_date": "YYYY-MM",
          "bullets": ["Actionable bullet 1", "Bullet 2", "Bullet 3"]
        }},
        ...
      ]
    }}

    Try to naturally integrate the following keywords when relevant:
    {keywords}

    ### Role Summary
    {job_summary}

    ### Key Responsibilities:
    {responsibilities}

    ### Original Work Experience:
    {json.dumps(experience)}

    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert resume writer with 20+ years of experience helping professionals break into the tech industry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        output = response.choices[0].message.content.strip()
        output = strip_json_codeblock(output)
        return json.loads(output)["work_experience"]
    except json.JSONDecodeError as e:
        print("[ERROR] Failed to parse GPT output.")
        raise e
    except Exception as e:
        print(f"[ERROR] An error occurred while tailoring work experience: {e}")
        raise

def generate_summary(tailored_experience, role, responsibilities, keywords):
    """Generate a concise professional summary based on tailored experience and job context."""
    prompt = f"""
    Using the following tailored work experience and job context, please generate a concise 50-70 word professional summary for a resume tailored to a {role} role.

    - Focus on years of experience, strengths, specialization, and value-add
    - Avoid overused phrases and passive voice
    - Write for a non-technical hiring manager
    - Use third-person and active language
    - Naturally integrate some of the keywords below when appropriate
    - Calculate years of experience from relevant work experience dates

    ### Key Responsibilities:
    {responsibilities}

    ### Keywords:
    {keywords}

    ### Tailored Work Experience:
    {json.dumps(tailored_experience)}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert resume writer with 20+ years of experience helping professionals break into the tech industry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        output = response.choices[0].message.content.strip()
        output = strip_json_codeblock(output)
        return output
    except Exception as e:
        print(f"[ERROR] An error occurred while generating summary: {e}")
        raise

def filter_and_suggest_skills(job_summary, responsibilities, keywords, existing_skills):
    """Filter existing skills and suggest new skills based on job description."""
    flat_skills = existing_skills
    prompt = f"""
    Here is a list of skills from a candidate's bio:
    {existing_skills}

    Her is information about the bob they are applying for:
    Job Summary:
    {job_summary}

    Key Responsibilities:
    {responsibilities}

    Relevant Keywords:
    {keywords}

    - Identify which existing candidate bio skills are relevant and should be included in the resume.
    - Then, suggest up to 5 **new** skills or tools that are not currently listed in the candidate's bio but would significantly improve the resume for this job.
    - If there are no skills or tools that are not currently listed but would significantly improve the resume for this job, do not list any.
    - There should be 4-7 categories with at least 3 items each in the selected_skills list.
    - There should be no category in suggested_skills that does not exist in selected_skills.
    - Ensure no suggested_skills already exist in the list of skills from a candidate's resume.

    Return ONLY valid JSON in the following format:

    {{
      "selected_skills": {{
        "Category Name": ["Skill 1", "Skill 2"]
      }},
      "suggested_skills": {{
        "Category Name": ["Skill 1", "Skill 2"]
      }}
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert resume writer with 20+ years of experience helping professionals break into the tech industry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        output = response.choices[0].message.content.strip()
        output = strip_json_codeblock(output)
        return json.loads(output)
    except json.JSONDecodeError as e:
        print("[ERROR] Failed to parse GPT skill output.")
        raise e
    except Exception as e:
        print(f"[ERROR] An error occurred while filtering and suggesting skills: {e}")
        raise



def render_resume_html_to_pdf(data, template_dir="templates/classic_resume", output_path="output/resume.pdf"):
    """Render the resume data to HTML and convert it to PDF."""
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("template.html")
    html_out = template.render(**data)

    # Save HTML to a temporary file
    html_file_path = "output/temp_resume.html"
    try:
        with open(html_file_path, "w") as f:
            f.write(html_out)
    except IOError as e:
        print(f"[ERROR] Failed to write HTML file: {e}")
        raise

    # Use Playwright to render PDF
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{os.path.abspath(html_file_path)}")
            page.pdf(path=output_path, format="A4")
            browser.close()
    except Exception as e:
        print(f"[ERROR] Failed to generate PDF: {e}")
        raise

def generate_output_filename(resume_json):
    """Generate a sanitized output filename based on resume data."""
    name = resume_json.get("name", "")
    target_company = resume_json.get("target_company", "")
    target_job_title = resume_json.get("target_job_title", "")
    
    def sanitize(text):
        return "".join(e for e in text if e.isalnum() or e == "_").lower()
    
    name_s = sanitize(name.replace(" ", "_"))
    company_s = sanitize(target_company.replace(" ", "_"))
    job_title_s = sanitize(target_job_title.replace(" ", "_"))
    return f"output/{name_s}_{company_s}_{job_title_s}.pdf"

# === Pipeline ===
if __name__ == "__main__":
    """Main execution block for generating a tailored resume."""
    try:
        print("[INFO] Loading resume data...")
        resume_yaml = load_resume()
        
        job_url = input("Enter the LinkedIn job URL: ").strip()
        print("[INFO] Fetching job description...")
        job_desc = fetch_job_description(job_url)

        # Step 1: Extract responsibilities, keywords, job title, and company name
        print("[INFO] Extracting responsibilities and keywords...")
        responsibility_data = extract_top_responsibilities(job_desc)

        # Step 2: Generate summary
        print("[INFO] Generating professional summary...")
        summary = generate_summary(
            resume_yaml["experience"],
            responsibility_data["target_job_title"],
            responsibility_data["responsibilities"],
            responsibility_data["keywords"]
        )

        # Step 3: Skills filtering
        print("[INFO] Filtering and suggesting skills...")
        skill_data = filter_and_suggest_skills(
            responsibility_data["job_summary"],
            responsibility_data["responsibilities"],
            responsibility_data["keywords"],
            resume_yaml["skills"]
        )
        selected_skills = skill_data["selected_skills"]
        suggested_skills = skill_data.get("suggested_skills", {})

        # Step 4: Ask user about adding suggested skills
        original_skills = set(resume_yaml["skills"])
        print("\n[INFO] Suggested Skills to Consider Adding:")
        for category, items in suggested_skills.items():
            for skill in items:
                if skill not in original_skills:
                    response = input(f"Would you like to include '{skill}' under '{category}'? (y/n): ").strip().lower()
                    if response == "y":
                        if category in selected_skills:
                            if skill not in selected_skills[category]:
                                selected_skills[category].append(skill)
                        else:
                            selected_skills[category] = [skill]
                        original_skills.add(skill)

        # Step 5: Update YAML flat skills list
        resume_yaml["skills"] = sorted(original_skills)

        # Step 6: Save updated YAML
        print("[INFO] Saving updated resume data...")
        with open("data/resume.yaml", "w") as f:
            yaml.dump(resume_yaml, f, default_flow_style=False, sort_keys=False)

        # Step 7: Load original projects section if included
        tailored_projects = resume_yaml.get("projects", []) if include_projects else []

        # Step 8: Calculate work experience word budget with tailored projects
        print("[INFO] Calculating work experience word budget...")
        flat_selected_skills = [skill for skills in selected_skills.values() for skill in skills]
        max_words = compute_work_experience_budget(summary, flat_selected_skills, resume_yaml["education"], tailored_projects)

        # Step 9: Tailor work experience
        print(f"[INFO] Tailoring work experience to fit within {max_words} words...")
        tailored_experience = tailor_work_experience(
            resume_yaml["experience"],
            responsibility_data["job_summary"],
            responsibility_data["responsibilities"],
            responsibility_data["keywords"],
            responsibility_data["target_job_title"],
            responsibility_data["target_company"],
            max_words,
            prune_irrelevant=prune_irrelevant,
            prioritize_relevance=prioritize_relevance
        )

        # Step 10: Format job dates
        print("[INFO] Formatting job dates...")
        for job in tailored_experience:
            job["start_date"] = format_date(job.get("start_date", ""))
            job["end_date"] = format_date(job.get("end_date", ""))


        # Step 11: Build resume JSON for rendering
        tailored_resume_json = {
            "name": resume_yaml.get("name"),
            "title": responsibility_data["target_job_title"],
            "email": resume_yaml["contact"].get("email"),
            "phone": resume_yaml["contact"].get("phone"),
            "location": resume_yaml["contact"].get("location"),
            "linkedin": resume_yaml["contact"].get("linkedin"),
            "github": resume_yaml["contact"].get("github"),
            "education": [
                {
                    "institution": edu.get("school"),
                    "degree": edu.get("degree")
                } for edu in resume_yaml.get("education", [])
            ],
            "projects": tailored_projects,
            "summary": summary,
            "skills": selected_skills,
            "work_experience": tailored_experience,
            "target_company": responsibility_data["target_company"],
            "target_job_title": responsibility_data["target_job_title"]
        }

        with open("output/sample_resume.json", "w") as f:
            json.dump(tailored_resume_json, f, indent=2)

        # Step 12: Render to PDF
        print("[INFO] Rendering resume to PDF...")
        output_file = generate_output_filename(tailored_resume_json)
        render_resume_html_to_pdf(tailored_resume_json, output_path=output_file)
        print("Resume Generated!")

    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")