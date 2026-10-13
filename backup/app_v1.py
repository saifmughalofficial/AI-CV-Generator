"""
CVForge AI - Streamlit Edition
A complete portfolio/interview-ready mock AI Digital CV Generator.

FREE / UNPAID DESIGN
- Streamlit UI
- SQLite database
- Optional Ollama local AI
- Rule-based fallback when Ollama is unavailable
- No paid AI API required

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "cvforge.db"
GENERATED_DIR = BASE_DIR / "generated"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        full_name TEXT DEFAULT '',
        title TEXT DEFAULT '',
        email TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        location TEXT DEFAULT '',
        linkedin TEXT DEFAULT '',
        github TEXT DEFAULT '',
        portfolio TEXT DEFAULT '',
        summary TEXT DEFAULT '',
        photo_path TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        skill_name TEXT,
        category TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        name TEXT,
        organization TEXT,
        date TEXT,
        credential_url TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_title TEXT,
        job_description TEXT,
        match_score REAL,
        matched_keywords TEXT,
        missing_keywords TEXT,
        created_at TEXT
    )
    """)

    if cur.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO profile (id, updated_at) VALUES (1, ?)",
            (datetime.now().isoformat(),)
        )

    conn.commit()
    conn.close()


init_db()


# ============================================================
# DATA HELPERS
# ============================================================

def get_profile():
    conn = db()
    row = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    conn.close()
    return dict(row)


def save_profile(data):
    conn = db()
    conn.execute("""
        UPDATE profile SET
        full_name=?, title=?, email=?, phone=?, location=?,
        linkedin=?, github=?, portfolio=?, summary=?,
        photo_path=?, updated_at=?
        WHERE id=1
    """, (
        data["full_name"], data["title"], data["email"], data["phone"],
        data["location"], data["linkedin"], data["github"],
        data["portfolio"], data["summary"], data.get("photo_path", ""),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def rows(table):
    conn = db()
    result = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
    conn.close()
    return result


def execute(sql, params=()):
    conn = db()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def delete_row(table, row_id):
    execute(f"DELETE FROM {table} WHERE id=?", (row_id,))


def clear_table(table):
    execute(f"DELETE FROM {table}")


def all_cv_text():
    p = get_profile()
    edu = rows("education")
    exp = rows("experience")
    skills = rows("skills")
    projects = rows("projects")
    certs = rows("certifications")

    chunks = [
        p["full_name"], p["title"], p["summary"],
        p["location"], p["linkedin"], p["github"], p["portfolio"]
    ]

    for x in edu:
        chunks += [x["degree"], x["institution"], x["grade"], x["description"]]

    for x in exp:
        chunks += [
            x["company"], x["position"], x["location"],
            x["responsibilities"], x["achievements"]
        ]

    for x in skills:
        chunks += [x["skill_name"], x["category"]]

    for x in projects:
        chunks += [x["name"], x["description"], x["technologies"]]

    for x in certs:
        chunks += [x["name"], x["organization"], x["date"]]

    return " ".join(str(x) for x in chunks if x)


# ============================================================
# LOCAL AI
# ============================================================

def ollama(prompt):
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
            answer = data.get("response", "").strip()
            return answer or None
    except Exception:
        return None


def mock_ai(feature, text):
    if feature == "summary":
        words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text)
        selected = ", ".join(words[:8])
        return (
            "Motivated professional with a practical background reflected "
            f"in the provided profile. Key areas include {selected or 'professional skills, projects, and experience'}. "
            "Demonstrates a structured approach to learning, project work, "
            "and professional development."
        )

    if feature == "experience":
        return (
            "• Managed assigned responsibilities using a structured and professional approach.\n"
            "• Supported day-to-day activities and contributed to team objectives.\n"
            "• Applied relevant skills to complete tasks and project requirements.\n"
            "• Maintained clear documentation and communication."
        )

    if feature == "project":
        return (
            "Developed and organized the project using the technologies and "
            "requirements provided. Focused on implementing the core "
            "functionality, usability, and maintainability of the solution."
        )

    if feature == "cover":
        return (
            "Dear Hiring Manager,\n\n"
            "I am writing to express my interest in this opportunity. "
            "My background, projects, and skills described in my CV provide "
            "a practical foundation for contributing to the role. I would "
            "welcome the opportunity to discuss my experience and how I can "
            "support your team.\n\n"
            "Kind regards,\nCandidate"
        )

    return "No AI result generated."


def generate_ai(feature, prompt, fallback_text):
    result = ollama(prompt)
    if result:
        return result, "Ollama local AI"
    return mock_ai(feature, fallback_text), "Local mock fallback"


# ============================================================
# ATS ANALYSIS
# ============================================================

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are",
    "you", "your", "our", "will", "have", "has", "into", "about",
    "their", "they", "role", "work", "using", "required",
    "requirements", "candidate", "team", "must", "should", "can",
    "to", "of", "in", "on", "a", "an", "is", "be", "as", "or"
}


def keywords(text):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text.lower())
    result = []
    for word in words:
        if word not in STOPWORDS and word not in result:
            result.append(word)
    return result[:80]


def analyze(cv, job):
    cv_set = set(keywords(cv))
    job_set = set(keywords(job))
    matched = sorted(cv_set & job_set)
    missing = sorted(job_set - cv_set)
    score = round((len(matched) / len(job_set)) * 100, 1) if job_set else 0
    return score, matched, missing


# ============================================================
# CV HTML GENERATION
# ============================================================

def esc(value):
    return html.escape(str(value or ""))


def build_cv_html(template="ATS-Friendly"):
    p = get_profile()
    edu = rows("education")
    exp = rows("experience")
    skills = rows("skills")
    projects = rows("projects")
    certs = rows("certifications")

    skill_html = "".join(
        f"<span class='skill'>{esc(x['skill_name'])}</span>"
        for x in skills
    )

    exp_html = ""
    for x in exp:
        exp_html += f"""
        <div class="item">
            <h3>{esc(x['position'])}</h3>
            <div class="meta">{esc(x['company'])} · {esc(x['location'])}
            · {esc(x['start_date'])} – {esc(x['end_date'])}</div>
            <p>{esc(x['responsibilities'])}</p>
            <p><strong>Achievements:</strong> {esc(x['achievements'])}</p>
        </div>
        """

    edu_html = "".join(f"""
        <div class="item">
            <h3>{esc(x['degree'])}</h3>
            <div class="meta">{esc(x['institution'])} ·
            {esc(x['start_year'])} – {esc(x['end_year'])}</div>
            <p>{esc(x['description'])}</p>
        </div>
    """ for x in edu)

    project_html = "".join(f"""
        <div class="item">
            <h3>{esc(x['name'])}</h3>
            <p>{esc(x['description'])}</p>
            <div class="meta">Technologies: {esc(x['technologies'])}</div>
        </div>
    """ for x in projects)

    cert_html = "".join(f"""
        <li><strong>{esc(x['name'])}</strong> — {esc(x['organization'])}
        ({esc(x['date'])})</li>
    """ for x in certs)

    if template == "Modern":
        extra = ".modern"
    elif template == "Professional":
        extra = ".professional"
    elif template == "Minimal":
        extra = ".minimal"
    else:
        extra = ".ats"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{esc(p['full_name'])} - CV</title>
<style>
body {{
    font-family: Arial, Helvetica, sans-serif;
    background:#f0f2f5;
    margin:0;
    color:#20242a;
}}
.page {{
    width:800px;
    margin:30px auto;
    background:#fff;
    padding:48px;
    box-sizing:border-box;
    box-shadow:0 3px 20px rgba(0,0,0,.10);
}}
h1 {{ margin:0 0 4px; font-size:32px; }}
h2 {{
    font-size:16px;
    text-transform:uppercase;
    letter-spacing:1px;
    border-bottom:2px solid #222;
    padding-bottom:6px;
    margin-top:28px;
}}
h3 {{ margin-bottom:3px; }}
.meta {{ color:#666; font-size:13px; }}
.item {{ margin-bottom:16px; }}
.skill {{
    display:inline-block;
    padding:5px 9px;
    margin:3px;
    border:1px solid #bbb;
    border-radius:12px;
    font-size:12px;
}}
.contact {{ color:#555; font-size:13px; margin:10px 0 22px; }}
.modern .page {{ border-top:8px solid #222; }}
.professional h2 {{ color:#333; }}
.minimal .page {{ box-shadow:none; }}
.ats .page {{ width:760px; box-shadow:none; }}
</style>
</head>
<body class="{extra[1:]}">
<div class="page">
<h1>{esc(p['full_name'])}</h1>
<h3>{esc(p['title'])}</h3>
<div class="contact">
{esc(p['email'])} · {esc(p['phone'])} · {esc(p['location'])}
</div>

<h2>Professional Summary</h2>
<p>{esc(p['summary'])}</p>

<h2>Experience</h2>
{exp_html or "<p>No experience added.</p>"}

<h2>Education</h2>
{edu_html or "<p>No education added.</p>"}

<h2>Skills</h2>
<div>{skill_html or "No skills added."}</div>

<h2>Projects</h2>
{project_html or "<p>No projects added.</p>"}

<h2>Certifications</h2>
<ul>{cert_html or "<li>No certifications added.</li>"}</ul>
</div>
</body>
</html>"""


# ============================================================
# STREAMLIT UI
# ============================================================

st.set_page_config(
    page_title="CVForge AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1250px;}
.hero {
    padding: 30px;
    border-radius: 18px;
    background: linear-gradient(135deg, #111827, #374151);
    color: white;
    margin-bottom: 25px;
}
.hero h1 {font-size: 42px; margin-bottom: 5px;}
.card {
    padding: 18px;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    background: white;
}
.small-muted {color:#6b7280;}
</style>
""", unsafe_allow_html=True)


def sidebar():
    st.sidebar.title("CVForge AI")
    st.sidebar.caption("Free / Unpaid CV & Career Platform")
    page = st.sidebar.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "👤 Personal Profile",
            "🎓 Education",
            "💼 Experience",
            "🛠️ Skills",
            "🚀 Projects",
            "🏆 Certifications",
            "🤖 AI Writer",
            "📊 ATS Job Analyzer",
            "🎯 Tailored CV",
            "✉️ Cover Letter",
            "🎨 CV Templates",
            "👁️ CV Preview",
            "🌐 Digital CV",
            "⚙️ Settings"
        ]
    )

    p = get_profile()
    completion_fields = [
        p["full_name"], p["title"], p["email"], p["phone"],
        p["location"], p["summary"]
    ]
    completion = int(
        sum(bool(x) for x in completion_fields) /
        len(completion_fields) * 100
    )

    st.sidebar.progress(completion / 100)
    st.sidebar.caption(f"Profile completion: {completion}%")
    return page


page = sidebar()


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":
    st.markdown("""
    <div class="hero">
        <h1>CVForge AI</h1>
        <p>Build an ATS-friendly CV, improve content with local AI,
        analyze jobs and create a digital CV.</p>
    </div>
    """, unsafe_allow_html=True)

    p = get_profile()
    cols = st.columns(4)
    metrics = [
        ("Profile", 1 if p["full_name"] else 0),
        ("Experience", len(rows("experience"))),
        ("Projects", len(rows("projects"))),
        ("Skills", len(rows("skills")))
    ]

    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    st.subheader("Quick Actions")
    a, b, c, d = st.columns(4)
    a.info("👤 Add your personal profile")
    b.info("🤖 Generate CV content")
    c.info("📊 Analyze a job description")
    d.info("📄 Preview your CV")

    st.divider()
    st.subheader("Project Architecture")
    st.code(
        "Streamlit UI → SQLite → Local Ollama (optional) → "
        "AI Writing → ATS Matching → CV HTML/PDF-ready output"
    )


# ============================================================
# PROFILE
# ============================================================

elif page == "👤 Personal Profile":
    st.title("👤 Personal Profile")
    p = get_profile()

    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full Name", p["full_name"])
        title = c2.text_input("Professional Title", p["title"])
        email = c1.text_input("Email", p["email"])
        phone = c2.text_input("Phone", p["phone"])
        location = c1.text_input("Location", p["location"])
        linkedin = c2.text_input("LinkedIn URL", p["linkedin"])
        github = c1.text_input("GitHub URL", p["github"])
        portfolio = c2.text_input("Portfolio URL", p["portfolio"])
        summary = st.text_area(
            "Professional Summary",
            p["summary"],
            height=160
        )

        submitted = st.form_submit_button("Save Profile", type="primary")

    if submitted:
        save_profile({
            "full_name": full_name,
            "title": title,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin": linkedin,
            "github": github,
            "portfolio": portfolio,
            "summary": summary,
            "photo_path": p["photo_path"]
        })
        st.success("Profile saved successfully.")


# ============================================================
# EDUCATION
# ============================================================

elif page == "🎓 Education":
    st.title("🎓 Education")

    with st.form("education_form"):
        degree = st.text_input("Degree")
        institution = st.text_input("Institution")
        c1, c2 = st.columns(2)
        start_year = c1.text_input("Start Year")
        end_year = c2.text_input("End Year")
        grade = st.text_input("CGPA / Grade")
        description = st.text_area("Description")
        add = st.form_submit_button("Add Education", type="primary")

    if add:
        execute("""
            INSERT INTO education
            (degree, institution, start_year, end_year, grade, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (degree, institution, start_year, end_year, grade, description))
        st.success("Education added.")

    st.divider()
    for x in rows("education"):
        with st.expander(f"{x['degree']} — {x['institution']}"):
            st.write(f"{x['start_year']} - {x['end_year']}")
            st.write(x["description"])
            if st.button("Delete", key=f"edu{x['id']}"):
                delete_row("education", x["id"])
                st.rerun()


# ============================================================
# EXPERIENCE
# ============================================================

elif page == "💼 Experience":
    st.title("💼 Experience")

    with st.form("experience_form"):
        company = st.text_input("Company")
        position = st.text_input("Job Title")
        location = st.text_input("Location")
        c1, c2 = st.columns(2)
        start_date = c1.text_input("Start Date")
        end_date = c2.text_input("End Date")
        responsibilities = st.text_area("Responsibilities")
        achievements = st.text_area("Achievements")
        add = st.form_submit_button("Add Experience", type="primary")

    if add:
        execute("""
            INSERT INTO experience
            (company, position, location, start_date, end_date,
             responsibilities, achievements)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            company, position, location, start_date, end_date,
            responsibilities, achievements
        ))
        st.success("Experience added.")

    st.divider()
    for x in rows("experience"):
        with st.expander(f"{x['position']} — {x['company']}"):
            st.write(x["responsibilities"])
            st.write("Achievements:", x["achievements"])
            if st.button("Delete", key=f"exp{x['id']}"):
                delete_row("experience", x["id"])
                st.rerun()


# ============================================================
# SKILLS
# ============================================================

elif page == "🛠️ Skills":
    st.title("🛠️ Skills")

    with st.form("skill_form"):
        skill = st.text_input("Skill")
        category = st.selectbox(
            "Category",
            ["Programming", "AI/ML", "Tools", "Soft Skills", "Languages", "Other"]
        )
        add = st.form_submit_button("Add Skill", type="primary")

    if add and skill.strip():
        execute(
            "INSERT INTO skills (skill_name, category) VALUES (?, ?)",
            (skill.strip(), category)
        )
        st.success("Skill added.")

    st.divider()
    for x in rows("skills"):
        c1, c2, c3 = st.columns([5, 3, 1])
        c1.write(x["skill_name"])
        c2.write(x["category"])
        if c3.button("X", key=f"skill{x['id']}"):
            delete_row("skills", x["id"])
            st.rerun()


# ============================================================
# PROJECTS
# ============================================================

elif page == "🚀 Projects":
    st.title("🚀 Projects")

    with st.form("project_form"):
        name = st.text_input("Project Name")
        description = st.text_area("Description")
        technologies = st.text_input("Technologies")
        github_url = st.text_input("GitHub URL")
        demo_url = st.text_input("Demo URL")
        add = st.form_submit_button("Add Project", type="primary")

    if add:
        execute("""
            INSERT INTO projects
            (name, description, technologies, github_url, demo_url)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, technologies, github_url, demo_url))
        st.success("Project added.")

    st.divider()
    for x in rows("projects"):
        with st.expander(x["name"]):
            st.write(x["description"])
            st.caption(f"Technologies: {x['technologies']}")
            if x["github_url"]:
                st.write(x["github_url"])
            if st.button("Delete", key=f"project{x['id']}"):
                delete_row("projects", x["id"])
                st.rerun()


# ============================================================
# CERTIFICATIONS
# ============================================================

elif page == "🏆 Certifications":
    st.title("🏆 Certifications")

    with st.form("cert_form"):
        name = st.text_input("Certificate Name")
        organization = st.text_input("Organization")
        date = st.text_input("Date")
        credential_url = st.text_input("Credential URL")
        add = st.form_submit_button("Add Certification", type="primary")

    if add:
        execute("""
            INSERT INTO certifications
            (name, organization, date, credential_url)
            VALUES (?, ?, ?, ?)
        """, (name, organization, date, credential_url))
        st.success("Certification added.")

    st.divider()
    for x in rows("certifications"):
        with st.expander(x["name"]):
            st.write(f"{x['organization']} · {x['date']}")
            if st.button("Delete", key=f"cert{x['id']}"):
                delete_row("certifications", x["id"])
                st.rerun()


# ============================================================
# AI WRITER
# ============================================================

elif page == "🤖 AI Writer":
    st.title("🤖 AI CV Writer")
    st.caption("Uses local Ollama if available. Otherwise the built-in mock engine works offline.")

    feature = st.selectbox(
        "Choose AI Feature",
        ["Professional Summary", "Improve Experience", "Improve Project"]
    )

    text = st.text_area(
        "Enter your information",
        height=220,
        placeholder="Paste your real CV information here..."
    )

    if st.button("Generate with AI", type="primary"):
        if not text.strip():
            st.warning("Enter some information first.")
        else:
            if feature == "Professional Summary":
                prompt = f"""
Write a concise ATS-friendly professional summary.
Use ONLY the facts supplied. Never invent experience or qualifications.

Information:
{text}
"""
                result, provider = generate_ai("summary", prompt, text)

            elif feature == "Improve Experience":
                prompt = f"""
Rewrite this experience into 3-5 strong professional CV bullets.
Preserve all facts and do not invent achievements.

Experience:
{text}
"""
                result, provider = generate_ai("experience", prompt, text)

            else:
                prompt = f"""
Create a professional project description using only these facts.
Do not invent technologies or results.

Project:
{text}
"""
                result, provider = generate_ai("project", prompt, text)

            st.success(f"Generated using: {provider}")
            st.text_area("Result", result, height=250)
            st.download_button(
                "Download TXT",
                result,
                file_name="cvforge_ai_result.txt",
                mime="text/plain"
            )


# ============================================================
# ATS
# ============================================================

elif page == "📊 ATS Job Analyzer":
    st.title("📊 ATS / Job Analyzer")
    st.caption(
        "This is a keyword matching indicator for the application, "
        "not a guaranteed score from a real employer's ATS."
    )

    job_title = st.text_input("Job Title")
    job_description = st.text_area(
        "Paste Job Description",
        height=300
    )

    if st.button("Analyze Job", type="primary"):
        if not job_description.strip():
            st.warning("Paste a job description first.")
        else:
            score, matched, missing = analyze(all_cv_text(), job_description)

            execute("""
                INSERT INTO analyses
                (job_title, job_description, match_score,
                 matched_keywords, missing_keywords, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job_title, job_description, score,
                json.dumps(matched), json.dumps(missing),
                datetime.now().isoformat()
            ))

            st.metric("Matching Indicator", f"{score}%")
            st.progress(score / 100)

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Matched Keywords")
                st.write(", ".join(matched) or "No strong keyword matches.")

            with c2:
                st.subheader("Missing Keywords")
                st.write(", ".join(missing) or "No obvious missing keywords.")

            st.subheader("Recommendations")
            st.write("- Add missing keywords only when they truthfully describe your skills.")
            st.write("- Keep experience bullets concise and factual.")
            st.write("- Use clear CV section headings.")
            st.write("- Do not add fake experience to improve the indicator.")


# ============================================================
# TAILORED CV
# ============================================================

elif page == "🎯 Tailored CV":
    st.title("🎯 Tailored CV Generator")

    job = st.text_area("Paste Target Job Description", height=280)

    if st.button("Generate Tailored CV Draft", type="primary"):
        if not job.strip():
            st.warning("Paste a job description first.")
        else:
            prompt = f"""
Tailor the candidate CV for the job below.
Use ONLY genuine information from the CV.
Do not invent skills, employers, qualifications, years or achievements.

JOB:
{job}

CV:
{all_cv_text()}
"""
            result, provider = generate_ai("summary", prompt, all_cv_text())
            st.success(f"Generated using: {provider}")
            st.text_area("Tailored Draft", result, height=400)
            st.download_button(
                "Download Tailored Draft",
                result,
                file_name="tailored_cv.txt",
                mime="text/plain"
            )


# ============================================================
# COVER LETTER
# ============================================================

elif page == "✉️ Cover Letter":
    st.title("✉️ Cover Letter Generator")

    c1, c2 = st.columns(2)
    job_title = c1.text_input("Job Title")
    company = c2.text_input("Company")

    job = st.text_area("Job Description", height=250)

    if st.button("Generate Cover Letter", type="primary"):
        if not job_title:
            st.warning("Enter the job title.")
        else:
            prompt = f"""
Write a professional cover letter.

Job title: {job_title}
Company: {company}
Job description:
{job}

Candidate CV:
{all_cv_text()}

Use only genuine candidate information.
Do not invent qualifications or experience.
"""
            result, provider = generate_ai("cover", prompt, all_cv_text())
            st.success(f"Generated using: {provider}")
            st.text_area("Cover Letter", result, height=400)
            st.download_button(
                "Download Cover Letter",
                result,
                file_name="cover_letter.txt",
                mime="text/plain"
            )


# ============================================================
# TEMPLATES
# ============================================================

elif page == "🎨 CV Templates":
    st.title("🎨 CV Templates")
    st.write("Choose the template used by the preview/export page.")

    template = st.radio(
        "Template",
        ["ATS-Friendly", "Modern", "Professional", "Minimal"],
        horizontal=True
    )
    st.session_state["template"] = template

    cards = {
        "ATS-Friendly": "Single-column, simple formatting and highly readable.",
        "Modern": "Contemporary visual hierarchy with a clean design.",
        "Professional": "Corporate-focused typography and spacing.",
        "Minimal": "Whitespace-focused and restrained visual styling."
    }

    st.info(cards[template])


# ============================================================
# PREVIEW
# ============================================================

elif page == "👁️ CV Preview":
    st.title("👁️ CV Preview")

    template = st.session_state.get("template", "ATS-Friendly")
    st.caption(f"Current template: {template}")

    cv_html = build_cv_html(template)

    st.components.v1.html(cv_html, height=1000, scrolling=True)

    st.download_button(
        "Download CV as HTML",
        cv_html,
        file_name="cvforge_cv.html",
        mime="text/html"
    )

    st.info(
        "Open the downloaded HTML in a browser and use Print → Save as PDF "
        "for a free PDF workflow."
    )


# ============================================================
# DIGITAL CV
# ============================================================

elif page == "🌐 Digital CV":
    st.title("🌐 Public Digital CV Preview")

    p = get_profile()
    st.markdown(f"## {esc(p['full_name'])}")
    st.caption(esc(p["title"]))
    st.write(p["summary"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Skills", len(rows("skills")))
    c2.metric("Experience", len(rows("experience")))
    c3.metric("Projects", len(rows("projects")))

    st.subheader("Skills")
    for x in rows("skills"):
        st.write(f"**{x['skill_name']}** — {x['category']}")

    st.subheader("Experience")
    for x in rows("experience"):
        st.write(f"### {x['position']} — {x['company']}")
        st.write(x["responsibilities"])

    st.subheader("Projects")
    for x in rows("projects"):
        st.write(f"### {x['name']}")
        st.write(x["description"])


# ============================================================
# SETTINGS
# ============================================================

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.write("### Local AI")
    st.code(f"Model: {OLLAMA_MODEL}\nURL: {OLLAMA_URL}")

    if st.button("Test Ollama"):
        result = ollama("Reply with exactly: CVForge AI local AI is working.")
        if result:
            st.success(result)
        else:
            st.error(
                "Ollama is not reachable. The application will continue "
                "using its free local mock fallback."
            )

    st.divider()

    st.write("### Database")
    st.write(f"Database: `{DB_PATH}`")

    if st.button("Clear All CV Data", type="secondary"):
        for table in ["education", "experience", "skills", "projects", "certifications", "analyses"]:
            clear_table(table)

        save_profile({
            "full_name": "", "title": "", "email": "", "phone": "",
            "location": "", "linkedin": "", "github": "", "portfolio": "",
            "summary": "", "photo_path": ""
        })

        st.success("All CV data cleared.")
        st.rerun()

    st.divider()
    st.caption("CVForge AI — mock portfolio project")
