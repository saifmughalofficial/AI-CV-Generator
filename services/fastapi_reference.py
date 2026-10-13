"""
SmartxCV - Mock Project
AI Digital CV Generator (Free / Unpaid Local Architecture)

This is a portfolio/interview-ready MOCK implementation based on the
provided AI Digital CV Generator blueprint.

It runs without paid AI APIs. If Ollama is installed and running, the
AI helper can use a local model. Otherwise, the application uses a
safe mock fallback so the demo still works.

Run:
    pip install fastapi uvicorn pydantic
    uvicorn app:app --reload

Optional local AI:
    Install Ollama separately and pull a model, e.g.:
        ollama pull llama3.2
    Then set:
        OLLAMA_MODEL=llama3.2

API docs:
    http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


APP_NAME = "SmartxCV"
DB_PATH = "cvforge.db"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

app = FastAPI(
    title=APP_NAME,
    description="Mock AI-powered CV/Resume Builder and Job Matching Platform",
    version="1.0.0",
)


# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            title TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin TEXT,
            github TEXT,
            portfolio TEXT,
            summary TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            degree TEXT,
            institution TEXT,
            start_year TEXT,
            end_year TEXT,
            grade TEXT,
            description TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            company TEXT,
            position TEXT,
            location TEXT,
            start_date TEXT,
            end_date TEXT,
            responsibilities TEXT,
            achievements TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            skill_name TEXT,
            category TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT,
            description TEXT,
            technologies TEXT,
            github_url TEXT,
            demo_url TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT,
            organization TEXT,
            date TEXT,
            credential_url TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            job_title TEXT,
            job_description TEXT,
            match_score REAL,
            missing_keywords TEXT,
            matched_keywords TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -------------------------------------------------------------------
# PYDANTIC MODELS
# -------------------------------------------------------------------

class ProfileCreate(BaseModel):
    full_name: str
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    summary: str = ""


class EducationCreate(BaseModel):
    profile_id: int
    degree: str = ""
    institution: str = ""
    start_year: str = ""
    end_year: str = ""
    grade: str = ""
    description: str = ""


class ExperienceCreate(BaseModel):
    profile_id: int
    company: str = ""
    position: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    responsibilities: str = ""
    achievements: str = ""


class SkillCreate(BaseModel):
    profile_id: int
    skill_name: str
    category: str = "Other"


class ProjectCreate(BaseModel):
    profile_id: int
    name: str
    description: str = ""
    technologies: str = ""
    github_url: str = ""
    demo_url: str = ""


class CertificationCreate(BaseModel):
    profile_id: int
    name: str
    organization: str = ""
    date: str = ""
    credential_url: str = ""


class AITextRequest(BaseModel):
    text: str
    context: str = ""


class JobAnalysisRequest(BaseModel):
    profile_id: int
    job_title: str = ""
    job_description: str


class CoverLetterRequest(BaseModel):
    profile_id: int
    job_title: str
    company: str = ""
    job_description: str = ""


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def row_to_dict(row):
    return dict(row) if row else None


def require_profile(profile_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    return row


def clean_keywords(text: str) -> List[str]:
    """
    Simple NLP-style keyword extraction for the mock project.
    This intentionally avoids paid APIs and external services.
    """
    stop_words = {
        "the", "and", "for", "with", "that", "this", "from", "are",
        "you", "your", "our", "will", "have", "has", "into", "about",
        "their", "they", "job", "role", "work", "years", "using",
        "experience", "required", "requirements", "candidate", "team",
        "must", "should", "can", "to", "of", "in", "on", "a", "an"
    }

    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text.lower())
    unique = []

    for word in words:
        if word not in stop_words and word not in unique:
            unique.append(word)

    return unique[:40]


def call_ollama(prompt: str) -> Optional[str]:
    """
    Calls Ollama only if a local model is available.
    No paid API is used.
    """
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception:
        return None


def mock_summary(text: str) -> str:
    return (
        "Motivated professional with a background reflected in the provided "
        "profile information. Demonstrates practical skills, project "
        "experience, and a willingness to contribute to a professional team. "
        "This summary is generated by the local mock engine and should be "
        "reviewed before use."
    )


def ai_generate(prompt: str, fallback: str) -> str:
    result = call_ollama(prompt)
    return result if result else fallback


def profile_text(profile_id: int) -> str:
    require_profile(profile_id)
    conn = get_db()

    profile = conn.execute(
        "SELECT * FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()

    education = conn.execute(
        "SELECT * FROM education WHERE profile_id = ?", (profile_id,)
    ).fetchall()

    experience = conn.execute(
        "SELECT * FROM experience WHERE profile_id = ?", (profile_id,)
    ).fetchall()

    skills = conn.execute(
        "SELECT * FROM skills WHERE profile_id = ?", (profile_id,)
    ).fetchall()

    projects = conn.execute(
        "SELECT * FROM projects WHERE profile_id = ?", (profile_id,)
    ).fetchall()

    certifications = conn.execute(
        "SELECT * FROM certifications WHERE profile_id = ?", (profile_id,)
    ).fetchall()

    conn.close()

    parts = [
        profile["full_name"],
        profile["title"],
        profile["summary"],
        profile["location"],
        " ".join(dict(x)["degree"] or "" for x in education),
        " ".join(dict(x)["institution"] or "" for x in education),
        " ".join(dict(x)["position"] or "" for x in experience),
        " ".join(dict(x)["company"] or "" for x in experience),
        " ".join(dict(x)["responsibilities"] or "" for x in experience),
        " ".join(dict(x)["achievements"] or "" for x in experience),
        " ".join(dict(x)["skill_name"] or "" for x in skills),
        " ".join(dict(x)["name"] or "" for x in projects),
        " ".join(dict(x)["description"] or "" for x in projects),
        " ".join(dict(x)["technologies"] or "" for x in projects),
        " ".join(dict(x)["name"] or "" for x in certifications),
    ]

    return " ".join(parts)


# -------------------------------------------------------------------
# HOME / DEMO UI
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SmartxCV</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f7fb;
                color: #20242b;
            }
            .card {
                background: white;
                padding: 28px;
                border-radius: 14px;
                margin-bottom: 20px;
                box-shadow: 0 4px 18px rgba(0,0,0,.07);
            }
            h1 { margin-bottom: 5px; }
            a {
                display: inline-block;
                padding: 12px 18px;
                background: #222;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-right: 8px;
            }
            code {
                background: #eee;
                padding: 3px 6px;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>SmartxCV</h1>
            <p>Free / unpaid AI Digital CV Generator mock project.</p>
            <p>
                Create profiles, improve CV content, analyze job descriptions,
                match keywords, and generate cover letters.
            </p>
            <a href="/docs">Open API Docs</a>
            <a href="/demo">Open Demo</a>
        </div>

        <div class="card">
            <h2>Architecture</h2>
            <p>FastAPI → SQLite → Optional Local Ollama → CV/ATS tools</p>
            <p>No paid AI API is required.</p>
        </div>
    </body>
    </html>
    """


@app.get("/demo", response_class=HTMLResponse)
def demo():
    return """
    <html>
    <head>
        <title>SmartxCV Demo</title>
        <style>
            body { font-family: Arial; max-width: 850px; margin: 40px auto; }
            textarea, input {
                width: 100%; padding: 10px; margin: 6px 0 15px;
                box-sizing: border-box;
            }
            button {
                padding: 11px 18px; cursor: pointer;
            }
            .box {
                border: 1px solid #ddd; padding: 20px;
                border-radius: 10px; margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <h1>SmartxCV — Mock Demo</h1>

        <div class="box">
            <h2>Create Profile</h2>
            <input id="name" placeholder="Full Name">
            <input id="title" placeholder="Professional Title">
            <input id="email" placeholder="Email">
            <textarea id="summary" placeholder="Professional Summary"></textarea>
            <button onclick="createProfile()">Create</button>
            <pre id="profileResult"></pre>
        </div>

        <div class="box">
            <h2>AI Summary</h2>
            <textarea id="summaryInput"
                placeholder="Enter your background, skills and experience"></textarea>
            <button onclick="generateSummary()">Generate Summary</button>
            <pre id="summaryResult"></pre>
        </div>

        <div class="box">
            <h2>Job Analyzer</h2>
            <input id="profileId" placeholder="Profile ID">
            <input id="jobTitle" placeholder="Job Title">
            <textarea id="jobDescription"
                placeholder="Paste job description here"></textarea>
            <button onclick="analyzeJob()">Analyze Job</button>
            <pre id="jobResult"></pre>
        </div>

        <script>
        async function createProfile() {
            const body = {
                full_name: document.getElementById("name").value,
                title: document.getElementById("title").value,
                email: document.getElementById("email").value,
                summary: document.getElementById("summary").value
            };

            const r = await fetch("/api/profile", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body)
            });

            document.getElementById("profileResult").textContent =
                JSON.stringify(await r.json(), null, 2);
        }

        async function generateSummary() {
            const body = {
                text: document.getElementById("summaryInput").value
            };

            const r = await fetch("/api/ai/summary", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body)
            });

            document.getElementById("summaryResult").textContent =
                JSON.stringify(await r.json(), null, 2);
        }

        async function analyzeJob() {
            const body = {
                profile_id: Number(document.getElementById("profileId").value),
                job_title: document.getElementById("jobTitle").value,
                job_description: document.getElementById("jobDescription").value
            };

            const r = await fetch("/api/ats/analyze", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body)
            });

            document.getElementById("jobResult").textContent =
                JSON.stringify(await r.json(), null, 2);
        }
        </script>
    </body>
    </html>
    """


# -------------------------------------------------------------------
# PROFILE API
# -------------------------------------------------------------------

@app.post("/api/profile")
def create_profile(data: ProfileCreate):
    conn = get_db()

    cur = conn.execute("""
        INSERT INTO profiles (
            full_name, title, email, phone, location,
            linkedin, github, portfolio, summary, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.full_name,
        data.title,
        data.email,
        data.phone,
        data.location,
        data.linkedin,
        data.github,
        data.portfolio,
        data.summary,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    profile_id = cur.lastrowid
    conn.close()

    return {
        "message": "Profile created successfully",
        "profile_id": profile_id
    }


@app.get("/api/profile/{profile_id}")
def get_profile(profile_id: int):
    profile = require_profile(profile_id)

    conn = get_db()
    education = conn.execute(
        "SELECT * FROM education WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    experience = conn.execute(
        "SELECT * FROM experience WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    skills = conn.execute(
        "SELECT * FROM skills WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    projects = conn.execute(
        "SELECT * FROM projects WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    certifications = conn.execute(
        "SELECT * FROM certifications WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    conn.close()

    return {
        "profile": row_to_dict(profile),
        "education": [row_to_dict(x) for x in education],
        "experience": [row_to_dict(x) for x in experience],
        "skills": [row_to_dict(x) for x in skills],
        "projects": [row_to_dict(x) for x in projects],
        "certifications": [row_to_dict(x) for x in certifications],
    }


# -------------------------------------------------------------------
# EDUCATION / EXPERIENCE / SKILLS / PROJECTS / CERTIFICATIONS
# -------------------------------------------------------------------

@app.post("/api/education")
def add_education(data: EducationCreate):
    require_profile(data.profile_id)

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO education (
            profile_id, degree, institution, start_year,
            end_year, grade, description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.profile_id, data.degree, data.institution,
        data.start_year, data.end_year, data.grade,
        data.description
    ))
    conn.commit()
    conn.close()

    return {"message": "Education added", "id": cur.lastrowid}


@app.post("/api/experience")
def add_experience(data: ExperienceCreate):
    require_profile(data.profile_id)

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO experience (
            profile_id, company, position, location,
            start_date, end_date, responsibilities, achievements
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.profile_id, data.company, data.position,
        data.location, data.start_date, data.end_date,
        data.responsibilities, data.achievements
    ))
    conn.commit()
    conn.close()

    return {"message": "Experience added", "id": cur.lastrowid}


@app.post("/api/skills")
def add_skill(data: SkillCreate):
    require_profile(data.profile_id)

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO skills (profile_id, skill_name, category)
        VALUES (?, ?, ?)
    """, (data.profile_id, data.skill_name, data.category))
    conn.commit()
    conn.close()

    return {"message": "Skill added", "id": cur.lastrowid}


@app.post("/api/projects")
def add_project(data: ProjectCreate):
    require_profile(data.profile_id)

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO projects (
            profile_id, name, description, technologies,
            github_url, demo_url
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.profile_id, data.name, data.description,
        data.technologies, data.github_url, data.demo_url
    ))
    conn.commit()
    conn.close()

    return {"message": "Project added", "id": cur.lastrowid}


@app.post("/api/certifications")
def add_certification(data: CertificationCreate):
    require_profile(data.profile_id)

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO certifications (
            profile_id, name, organization, date, credential_url
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.profile_id, data.name, data.organization,
        data.date, data.credential_url
    ))
    conn.commit()
    conn.close()

    return {"message": "Certification added", "id": cur.lastrowid}


# -------------------------------------------------------------------
# AI FEATURES
# -------------------------------------------------------------------

@app.post("/api/ai/summary")
def generate_summary(data: AITextRequest):
    prompt = f"""
You are a professional CV writer.

Create a concise ATS-friendly professional summary using ONLY the
information provided by the user.

Do not invent employers, years of experience, degrees, certifications,
achievements, or technologies.

User information:
{data.text}

Return one polished paragraph.
"""

    fallback = mock_summary(data.text)

    return {
        "feature": "AI Summary Generator",
        "provider": "Ollama local model or mock fallback",
        "summary": ai_generate(prompt, fallback)
    }


@app.post("/api/ai/improve-experience")
def improve_experience(data: AITextRequest):
    prompt = f"""
Rewrite the following CV experience into strong professional bullet
points. Preserve factual information and do not invent achievements.

Experience:
{data.text}

Return 3-5 concise bullet points.
"""

    fallback = (
        "• Improved and organized responsibilities into professional CV language.\n"
        "• Supported day-to-day tasks while maintaining clear communication.\n"
        "• Contributed to assigned projects and operational activities."
    )

    return {
        "feature": "Experience Improver",
        "result": ai_generate(prompt, fallback)
    }


@app.post("/api/ai/improve-project")
def improve_project(data: AITextRequest):
    prompt = f"""
Create a professional CV project description from the information below.
Do not add technologies or results that were not provided.

Project information:
{data.text}

Return a short description followed by 2-3 achievement-style bullets.
"""

    fallback = (
        "Developed a practical project based on the provided requirements "
        "and technologies. Focused on implementing the core functionality "
        "and presenting the project in a clear, professional format."
    )

    return {
        "feature": "Project Description Generator",
        "result": ai_generate(prompt, fallback)
    }


@app.post("/api/ai/categorize-skills")
def categorize_skills(data: AITextRequest):
    skills = clean_keywords(data.text)

    categories = {
        "Programming": [],
        "AI/ML": [],
        "Tools": [],
        "Soft Skills": [],
        "Other": []
    }

    ai_terms = {
        "python", "machine", "learning", "tensorflow", "pytorch",
        "opencv", "nlp", "ai", "artificial", "intelligence"
    }

    programming_terms = {
        "python", "java", "javascript", "typescript", "php",
        "c++", "sql", "html", "css"
    }

    tool_terms = {
        "git", "github", "docker", "figma", "photoshop",
        "excel", "fastapi", "streamlit"
    }

    soft_terms = {
        "communication", "leadership", "teamwork",
        "management", "problem", "presentation"
    }

    for skill in skills:
        if skill in ai_terms:
            categories["AI/ML"].append(skill)
        elif skill in programming_terms:
            categories["Programming"].append(skill)
        elif skill in tool_terms:
            categories["Tools"].append(skill)
        elif skill in soft_terms:
            categories["Soft Skills"].append(skill)
        else:
            categories["Other"].append(skill)

    return {
        "feature": "Skills Categorizer",
        "categories": categories
    }


# -------------------------------------------------------------------
# ATS / JOB MATCHING
# -------------------------------------------------------------------

@app.post("/api/ats/analyze")
def analyze_job(data: JobAnalysisRequest):
    cv_text = profile_text(data.profile_id)

    cv_keywords = set(clean_keywords(cv_text))
    job_keywords = set(clean_keywords(data.job_description))

    matched = sorted(cv_keywords.intersection(job_keywords))
    missing = sorted(job_keywords.difference(cv_keywords))

    if job_keywords:
        score = round((len(matched) / len(job_keywords)) * 100, 2)
    else:
        score = 0

    conn = get_db()
    conn.execute("""
        INSERT INTO job_analyses (
            profile_id, job_title, job_description, match_score,
            missing_keywords, matched_keywords, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.profile_id,
        data.job_title,
        data.job_description,
        score,
        json.dumps(missing),
        json.dumps(matched),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

    return {
        "feature": "ATS / Job Analyzer",
        "notice": (
            "This is a matching indicator for the application demo, "
            "not a guaranteed score from a real employer's ATS."
        ),
        "match_indicator": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "recommendations": [
            "Review missing keywords and add only truthful skills.",
            "Use clear section headings.",
            "Keep experience bullets concise and factual.",
            "Avoid adding experience that the candidate does not have."
        ]
    }


@app.post("/api/ats/tailor")
def tailor_cv(data: JobAnalysisRequest):
    cv_text = profile_text(data.profile_id)

    prompt = f"""
Tailor the following CV content for the target job.

IMPORTANT:
- Use only genuine information already present in the CV.
- Do not invent skills, employers, degrees, certifications, years,
  achievements, or experience.
- Improve wording and emphasize relevant existing information.

TARGET JOB:
{data.job_description}

CURRENT CV:
{cv_text}
"""

    fallback = (
        "Tailored CV draft:\n\n"
        "Emphasize the candidate's existing skills and experience that "
        "overlap with the target role. Add missing keywords only when they "
        "accurately describe the candidate's real background."
    )

    return {
        "feature": "Tailored CV Generator",
        "result": ai_generate(prompt, fallback)
    }


@app.post("/api/cover-letter")
def generate_cover_letter(data: CoverLetterRequest):
    cv_text = profile_text(data.profile_id)

    prompt = f"""
Write a concise professional cover letter for this candidate.

Job title: {data.job_title}
Company: {data.company}
Job description:
{data.job_description}

Candidate CV:
{cv_text}

Use only information from the candidate CV. Do not invent experience,
qualifications, achievements, or company-specific facts.
"""

    fallback = (
        f"Dear Hiring Manager,\\n\\n"
        f"I am writing to express my interest in the {data.job_title} "
        f"position. My background and project experience align with several "
        f"of the requirements described for this role. I would welcome the "
        f"opportunity to discuss how my existing skills can contribute to "
        f"your team.\\n\\n"
        f"Kind regards,\\n"
        f"Candidate"
    )

    return {
        "feature": "Cover Letter Generator",
        "result": ai_generate(prompt, fallback)
    }


# -------------------------------------------------------------------
# CV VIEW / SIMPLE HTML EXPORT
# -------------------------------------------------------------------

@app.get("/api/cv/{profile_id}", response_class=HTMLResponse)
def cv_preview(profile_id: int):
    require_profile(profile_id)

    conn = get_db()
    profile = conn.execute(
        "SELECT * FROM profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    education = conn.execute(
        "SELECT * FROM education WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    experience = conn.execute(
        "SELECT * FROM experience WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    skills = conn.execute(
        "SELECT * FROM skills WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    projects = conn.execute(
        "SELECT * FROM projects WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    certifications = conn.execute(
        "SELECT * FROM certifications WHERE profile_id = ?", (profile_id,)
    ).fetchall()
    conn.close()

    skill_html = "".join(
        f"<li>{x['skill_name']} — {x['category']}</li>" for x in skills
    )

    experience_html = "".join(
        f"""
        <div>
            <h3>{x['position']} — {x['company']}</h3>
            <p>{x['start_date']} - {x['end_date']}</p>
            <p>{x['responsibilities']}</p>
            <p><b>Achievements:</b> {x['achievements']}</p>
        </div>
        """
        for x in experience
    )

    education_html = "".join(
        f"""
        <div>
            <h3>{x['degree']}</h3>
            <p>{x['institution']} ({x['start_year']} - {x['end_year']})</p>
            <p>{x['description']}</p>
        </div>
        """
        for x in education
    )

    project_html = "".join(
        f"""
        <div>
            <h3>{x['name']}</h3>
            <p>{x['description']}</p>
            <p><b>Technologies:</b> {x['technologies']}</p>
        </div>
        """
        for x in projects
    )

    certification_html = "".join(
        f"<li>{x['name']} — {x['organization']} ({x['date']})</li>"
        for x in certifications
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{profile['full_name']} - CV</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 850px;
                margin: 40px auto;
                line-height: 1.55;
                color: #222;
            }}
            h1 {{ margin-bottom: 0; }}
            h2 {{
                border-bottom: 2px solid #222;
                padding-bottom: 5px;
                margin-top: 28px;
            }}
            .muted {{ color: #666; }}
        </style>
    </head>
    <body>
        <h1>{profile['full_name']}</h1>
        <h3>{profile['title']}</h3>
        <p class="muted">
            {profile['email']} | {profile['phone']} | {profile['location']}
        </p>

        <h2>Professional Summary</h2>
        <p>{profile['summary']}</p>

        <h2>Experience</h2>
        {experience_html or "<p>No experience added.</p>"}

        <h2>Education</h2>
        {education_html or "<p>No education added.</p>"}

        <h2>Skills</h2>
        <ul>{skill_html or "<li>No skills added.</li>"}</ul>

        <h2>Projects</h2>
        {project_html or "<p>No projects added.</p>"}

        <h2>Certifications</h2>
        <ul>{certification_html or "<li>No certifications added.</li>"}</ul>
    </body>
    </html>
    """


# -------------------------------------------------------------------
# DIGITAL CV
# -------------------------------------------------------------------

@app.get("/api/digital-cv/{profile_id}", response_class=HTMLResponse)
def digital_cv(profile_id: int):
    require_profile(profile_id)
    return cv_preview(profile_id)


# -------------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "project": APP_NAME,
        "database": DB_PATH,
        "local_ai": "Ollama optional",
        "model": OLLAMA_MODEL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
