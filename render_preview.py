import json
from resume_generator import render_resume_html_to_pdf

with open("output/sample_resume.json", "r") as f:
    resume_data = json.load(f)

render_resume_html_to_pdf(resume_data, output_path="output/preview.pdf")