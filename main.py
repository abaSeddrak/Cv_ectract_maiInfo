from fastapi import FastAPI, UploadFile, File
import pdfplumber
from docx import Document
import tempfile
import os
import re
import spacy
import phonenumbers

# ---------------- INIT ----------------
app = FastAPI()
nlp = spacy.load("en_core_web_sm")

# ---------------- SKILLS DB ----------------
SKILLS_DB = [
    "python", "java", "flutter", "dart", "react",
    "machine learning", "deep learning", "nlp",
    "sql", "fastapi", "django", "aws"
]

# ---------------- HELPERS ----------------
def extract_linkedin(text):
    pattern = r'(https?://)?(www\.)?linkedin\.com/in/[a-zA-Z0-9\-_]+'
    match = re.search(pattern, text)

    if match:
        url = match.group()
        if not url.startswith("http"):
            url = "https://" + url
        return url

    return None
def extract_job_title(text):
    keywords = [
        "developer", "engineer", "designer",
        "manager", "scientist", "specialist",
        "flutter", "backend", "frontend", "data"
    ]

    lines = text.split("\n")

    for line in lines:
        line_lower = line.lower()

        if any(k in line_lower for k in keywords):
            return line.strip()

    return None

def extract_github(text):
    pattern = r'(https?://)?(www\.)?github\.com/[a-zA-Z0-9\-_]+'
    match = re.search(pattern, text)

    if match:
        url = match.group()
        if not url.startswith("http"):
            url = "https://" + url
        return url

    return None

def extract_email(text):
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+', text)
    return match.group() if match else None


def extract_phone(text):
    try:
        for match in phonenumbers.PhoneNumberMatcher(text, "EG"):
            return phonenumbers.format_number(
                match.number,
                phonenumbers.PhoneNumberFormat.E164
            )
    except:
        pass
    return None


def extract_name(text):
    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text

    # fallback
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if line and "@" not in line and not any(char.isdigit() for char in line):
            if 2 <= len(line.split()) <= 4:
                return line

    return None


def extract_skills(text):
    text_lower = text.lower()
    found = []

    for skill in SKILLS_DB:
        if skill in text_lower:
            found.append(skill)

    return list(set(found))


def extract_experience(text):
    years = re.findall(r'(\d+)\+?\s*(years|yrs)', text.lower())

    if years:
        return max([int(y[0]) for y in years])

    return 0


def extract_education(text):
    keywords = ["university", "bachelor", "bsc", "msc", "master", "degree"]
    text_lower = text.lower()

    return any(k in text_lower for k in keywords)


def score_candidate(skills, experience):
    score = 0
    score += len(skills) * 10
    score += experience * 5
    return min(score, 100)

# ---------------- API ----------------

@app.post("/analyze-cv")
async def analyze_cv(file: UploadFile = File(...)):

    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    text = ""

    try:
        # -------- PDF --------
        if suffix.lower() == ".pdf":
            with pdfplumber.open(temp_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

        # -------- DOCX --------
        elif suffix.lower() == ".docx":
            doc = Document(temp_path)
            text = "\n".join(p.text for p in doc.paragraphs)

        else:
            return {"error": "Unsupported file type"}

        # -------- AI EXTRACTION --------
        name = extract_name(text)
        email = extract_email(text)
        phone = extract_phone(text)
        skills = extract_skills(text)
        experience = extract_experience(text)
        education = extract_education(text)
        linkedin = extract_linkedin(text)
        github = extract_github(text)
        jobTitle = extract_job_title(text)
        score = score_candidate(skills, experience)

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "experience_years": experience,
            "education": education,
            "candidate_score": score,
            "linkedin": linkedin,
            "github": github,
            "jobTitle": jobTitle
        }

    finally:
        os.remove(temp_path)