"""
SmartxCV - Streamlit Edition (v3)
A portfolio/interview-ready AI Digital CV Generator.

FREE / UNPAID DESIGN
- Step-by-step CV builder with live preview, 3D hero and website CV
- SQLite database
- Optional Ollama local AI
- Smart rule-based fallback when Ollama is unavailable
- No paid AI API required

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

import streamlit as st

import cv_templates as tpl
import ui_effects as fx

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "cvforge.db"
PHOTO_DIR = BASE_DIR / "data" / "photos"
GENERATED_DIR = BASE_DIR / "generated"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_TAGS_URL = OLLAMA_URL.rsplit("/api/", 1)[0] + "/api/tags"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

for folder in (DB_PATH.parent, PHOTO_DIR, GENERATED_DIR):
    folder.mkdir(parents=True, exist_ok=True)

ENTRY_TABLES = ["education", "experience", "skills", "projects", "certifications"]
SKILL_CATEGORIES = ["Programming", "AI/ML", "Tools", "Soft Skills", "Languages", "Other"]
LEVELS = {1: "Beginner", 2: "Elementary", 3: "Intermediate", 4: "Advanced", 5: "Expert"}


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(cur, table, column, decl):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # v2 migrations (safe on existing databases)
    ensure_column(cur, "skills", "level", "INTEGER DEFAULT 3")
    ensure_column(cur, "analyses", "company", "TEXT DEFAULT ''")
    for table in ENTRY_TABLES:
        ensure_column(cur, table, "sort_order", "INTEGER DEFAULT 0")

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

PROFILE_FIELDS = ["full_name", "title", "email", "phone", "location",
                  "linkedin", "github", "portfolio", "summary"]


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


def update_profile_field(field, value):
    p = get_profile()
    p[field] = value
    save_profile(p)


def rows(table):
    order = "id DESC" if table == "analyses" else "sort_order, id"
    conn = db()
    result = [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()]
    conn.close()
    return result


def execute(sql, params=()):
    conn = db()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def insert_row(table, data):
    conn = db()
    next_order = conn.execute(f"SELECT COALESCE(MAX(sort_order), 0) + 1 FROM {table}").fetchone()[0]
    conn.close()
    data = {**data, "sort_order": next_order}
    cols = ", ".join(data)
    marks = ", ".join("?" for _ in data)
    return execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(data.values()))


def update_row(table, row_id, data):
    sets = ", ".join(f"{k}=?" for k in data)
    execute(f"UPDATE {table} SET {sets} WHERE id=?", (*data.values(), row_id))


def delete_row(table, row_id):
    execute(f"DELETE FROM {table} WHERE id=?", (row_id,))


def move_row(table, row_id, direction):
    ids = [r["id"] for r in rows(table)]
    i = ids.index(row_id)
    j = i + direction
    if not 0 <= j < len(ids):
        return
    ids[i], ids[j] = ids[j], ids[i]
    conn = db()
    conn.executemany(f"UPDATE {table} SET sort_order=? WHERE id=?", [(n, rid) for n, rid in enumerate(ids)])
    conn.commit()
    conn.close()


def clear_table(table):
    execute(f"DELETE FROM {table}")


def get_setting(key, default=""):
    conn = db()
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, str(value)))


def photo_abs(photo_path):
    if not photo_path:
        return ""
    p = Path(photo_path)
    p = p if p.is_absolute() else BASE_DIR / p
    return str(p) if p.is_file() else ""


def load_cv():
    profile = get_profile()
    profile["photo_abs"] = photo_abs(profile.get("photo_path"))
    cv = {"profile": profile}
    for table in ENTRY_TABLES:
        cv[table] = rows(table)
    return cv


def all_cv_text(cv=None):
    cv = cv or load_cv()
    p = cv["profile"]
    chunks = [p["full_name"], p["title"], p["summary"], p["location"],
              p["linkedin"], p["github"], p["portfolio"]]

    for x in cv["education"]:
        chunks += [x["degree"], x["institution"], x["grade"], x["description"]]
    for x in cv["experience"]:
        chunks += [x["company"], x["position"], x["location"], x["responsibilities"], x["achievements"]]
    for x in cv["skills"]:
        chunks += [x["skill_name"], x["category"]]
    for x in cv["projects"]:
        chunks += [x["name"], x["description"], x["technologies"]]
    for x in cv["certifications"]:
        chunks += [x["name"], x["organization"], x["date"]]

    return " ".join(str(x) for x in chunks if x)


def theme_accent():
    return get_setting("accent", "#14584a")


ASSETS_DIR = BASE_DIR / "assets"
LOGO_ICON = ASSETS_DIR / "smartxcv_logo_64.png"
LOGO_MEDIUM = ASSETS_DIR / "smartxcv_logo_256.png"


@st.cache_data
def logo_uri(path=str(LOGO_MEDIUM)):
    return tpl.photo_data_uri(path)


def current_template():
    t = get_setting("template", "ATS-Friendly")
    return t if t in tpl.TEMPLATES else "ATS-Friendly"


# ============================================================
# BACKUP / RESTORE / DEMO DATA
# ============================================================

ENTRY_FIELDS = {
    "education": ["degree", "institution", "start_year", "end_year", "grade", "description"],
    "experience": ["company", "position", "location", "start_date", "end_date", "responsibilities", "achievements"],
    "skills": ["skill_name", "category", "level"],
    "projects": ["name", "description", "technologies", "github_url", "demo_url"],
    "certifications": ["name", "organization", "date", "credential_url"],
}


def export_data():
    cv = load_cv()
    data = {"app": "SmartxCV", "version": 2, "exported_at": datetime.now().isoformat(),
            "profile": {k: cv["profile"].get(k, "") for k in PROFILE_FIELDS}}
    for table, fields in ENTRY_FIELDS.items():
        data[table] = [{k: x.get(k) for k in fields} for x in cv[table]]
    return data


def import_data(data):
    if not isinstance(data, dict) or not isinstance(data.get("profile"), dict):
        raise ValueError("This file is not a SmartxCV backup.")
    profile = {k: str(data["profile"].get(k) or "") for k in PROFILE_FIELDS}
    profile["photo_path"] = get_profile().get("photo_path", "")
    save_profile(profile)
    for table, fields in ENTRY_FIELDS.items():
        clear_table(table)
        for item in data.get(table) or []:
            if isinstance(item, dict):
                insert_row(table, {k: item.get(k) for k in fields if k in item})


DEMO_DATA = {
    "profile": {
        "full_name": "Alex Morgan",
        "title": "Data Analyst",
        "email": "alex.morgan@example.com",
        "phone": "+44 7700 900123",
        "location": "Manchester, UK",
        "linkedin": "linkedin.com/in/alexmorgan",
        "github": "github.com/alexmorgan",
        "portfolio": "alexmorgan.dev",
        "summary": (
            "Data Analyst with 3 years of experience turning raw data into clear business decisions. "
            "Skilled in Python, SQL and Power BI, with a track record of automating reporting and "
            "building dashboards used by leadership teams. Comfortable working with stakeholders to "
            "define metrics and communicate insights."
        ),
    },
    "education": [{
        "degree": "BSc Computer Science", "institution": "University of Manchester",
        "start_year": "2018", "end_year": "2021", "grade": "First Class Honours",
        "description": "Dissertation on customer churn prediction using machine learning.",
    }],
    "experience": [
        {
            "company": "Northwind Retail", "position": "Data Analyst", "location": "Manchester",
            "start_date": "Jan 2023", "end_date": "Present",
            "responsibilities": ("Built and maintained Power BI dashboards for sales and inventory\n"
                                 "Wrote SQL queries to analyse 5M+ transaction records\n"
                                 "Partnered with marketing to define campaign KPIs"),
            "achievements": ("Automated weekly reporting, saving 10 hours per week\n"
                             "Reduced stock-outs by 12% through demand trend analysis"),
        },
        {
            "company": "Brightpath Consulting", "position": "Junior Data Analyst", "location": "Leeds",
            "start_date": "Jul 2021", "end_date": "Dec 2022",
            "responsibilities": ("Cleaned and prepared client datasets in Python (pandas)\n"
                                 "Created Excel models for financial forecasting\n"
                                 "Presented findings to client stakeholders"),
            "achievements": "Delivered 8 client analytics projects on schedule",
        },
    ],
    "skills": [
        {"skill_name": n, "category": c, "level": l} for n, c, l in [
            ("Python", "Programming", 5), ("SQL", "Programming", 5), ("Power BI", "Tools", 4),
            ("Excel", "Tools", 4), ("Tableau", "Tools", 3), ("pandas", "AI/ML", 4),
            ("scikit-learn", "AI/ML", 3), ("Data visualisation", "Other", 4),
            ("Communication", "Soft Skills", 4), ("Stakeholder management", "Soft Skills", 3),
            ("English", "Languages", 5),
        ]
    ],
    "projects": [
        {
            "name": "Customer Churn Predictor",
            "description": "Machine learning model predicting telecom customer churn with 87% accuracy, served through a Streamlit app.",
            "technologies": "Python, scikit-learn, Streamlit", "github_url": "github.com/alexmorgan/churn", "demo_url": "",
        },
        {
            "name": "Sales Insights Dashboard",
            "description": "Interactive Power BI dashboard tracking revenue, margin and regional performance.",
            "technologies": "Power BI, SQL, DAX", "github_url": "", "demo_url": "",
        },
    ],
    "certifications": [
        {"name": "Microsoft Certified: Power BI Data Analyst Associate", "organization": "Microsoft",
         "date": "2023", "credential_url": ""},
        {"name": "Google Data Analytics Certificate", "organization": "Google / Coursera",
         "date": "2022", "credential_url": ""},
    ],
}


def clear_all_data():
    for table in ENTRY_TABLES + ["analyses"]:
        clear_table(table)
    old_photo = photo_abs(get_profile().get("photo_path"))
    if old_photo:
        Path(old_photo).unlink(missing_ok=True)
    save_profile({k: "" for k in PROFILE_FIELDS + ["photo_path"]})


# ============================================================
# LOCAL AI
# ============================================================

def ollama_models():
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return None


def ai_online(refresh=False):
    if refresh or "ai_online" not in st.session_state:
        models = ollama_models()
        st.session_state["ai_online"] = models is not None
        st.session_state["ai_models"] = models or []
    return st.session_state["ai_online"]


def ai_model():
    return get_setting("ollama_model", OLLAMA_MODEL)


def ollama(prompt):
    payload = json.dumps({"model": ai_model(), "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            answer = data.get("response", "").strip()
            return answer or None
    except Exception:
        return None


# ---------- offline "smart" engine: rewrites only the facts it is given ----------

REWRITES = [
    (r"^(i\s+)?(was\s+)?responsible for\s+", "Managed "),
    (r"^(i\s+)?was in charge of\s+", "Led "),
    (r"^(i\s+)?worked on\s+", "Contributed to "),
    (r"^(i\s+)?worked with\s+", "Collaborated with "),
    (r"^(i\s+)?helped with\s+", "Supported "),
    (r"^(i\s+)?made\s+", "Created "),
    (r"^(i\s+)?did\s+", "Performed "),
    (r"^(i\s+)?used\s+", "Applied "),
    (r"^(i\s+)?(have\s+)?(been\s+)?(doing|working as)\s+", "Worked as "),
    (r"^i\s+", ""),
]


def human_list(items):
    items = [str(x) for x in items if x]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def polish_line(fragment):
    line = fragment.strip().lstrip("•-*–· ").strip().rstrip(".;,")
    for pattern, repl in REWRITES:
        new = re.sub(pattern, repl, line, count=1, flags=re.I)
        if new != line:
            line = new
            break
    return line[:1].upper() + line[1:] if line else ""


def polish_bullets(text):
    fragments = re.split(r"[\n;]+|(?<=[.!?])\s+", text or "")
    lines = [polish_line(f) for f in fragments]
    lines = [l for l in lines if len(l) > 2]
    return "\n".join(f"• {l}" for l in lines) if lines else (text or "")


def lower_first(text):
    """Lowercase the first letter unless it starts an acronym (SQL, CRM...)."""
    return text[:1].lower() + text[1:] if text[1:2].islower() else text


def top_skills(cv, n=5, prefer=()):
    """Job-relevant skills first, then technical skills, then by proficiency."""
    prefer = {k.lower() for k in prefer}
    ranked = sorted(cv["skills"], key=lambda s: (
        s["skill_name"].lower() not in prefer,
        s.get("category") in ("Soft Skills", "Languages"),
        -(s.get("level") or 3),
    ))
    return [s["skill_name"] for s in ranked[:n]]


def mock_summary(cv, text="", prefer=()):
    p = cv["profile"]
    title = p.get("title") or "Professional"
    skills = top_skills(cv, 5, prefer)
    extra = [k for k in keywords_ranked(text)[:4] if k not in {s.lower() for s in skills}]
    parts = [f"{title} with hands-on experience in {human_list(skills)}." if skills
             else f"{title} with a practical, results-focused background."]
    if cv["experience"]:
        x = cv["experience"][0]
        parts.append(f"Most recently worked as {x['position']} at {x['company']}"
                     + (f", alongside earlier roles at {human_list(e['company'] for e in cv['experience'][1:3])}."
                        if len(cv["experience"]) > 1 else "."))
    if extra:
        parts.append(f"Areas of focus include {human_list(extra)}.")
    if cv["projects"]:
        parts.append(f"Has delivered projects such as {human_list(x['name'] for x in cv['projects'][:2])}.")
    if cv["education"]:
        e = cv["education"][0]
        parts.append(f"Holds a {e['degree']} from {e['institution']}.")
    return " ".join(parts)


def mock_project(text):
    lines = [polish_line(f) for f in re.split(r"[\n;]+|(?<=[.!?])\s+", text or "")]
    lines = [l for l in lines if len(l) > 2]
    if not lines:
        return text
    return lines[0] + "." + ("\n" + "\n".join(f"• {l}" for l in lines[1:]) if len(lines) > 1 else "")


def mock_cover(cv, job_title, company, job):
    p = cv["profile"]
    matched = analyze(all_cv_text(cv), job)["matched"] if job.strip() else []
    skills = top_skills(cv, 4, prefer=matched)
    at = f" at {company}" if company else ""
    out = ["Dear Hiring Manager,", ""]
    intro = f"I am writing to apply for the {job_title} position{at}."
    if p.get("title"):
        intro += f" As a {p['title']}"
        intro += f" currently working at {cv['experience'][0]['company']}," if cv["experience"] else ","
        intro += f" I have built practical skills in {human_list(skills)}" if skills else " I have built a strong practical foundation"
        intro += " that align closely with this role."
    out.append(intro)

    if cv["experience"]:
        x = cv["experience"][0]
        resp = [lower_first(polish_line(l)) for l in tpl.split_lines(x["responsibilities"])[:2]]
        ach = tpl.split_lines(x["achievements"])[:1]
        para = f"In my role as {x['position']} at {x['company']}, I {human_list(resp)}." if resp else ""
        if ach:
            para += f" A highlight was this result: {ach[0].rstrip('.')}."
        if para:
            out += ["", para.strip()]

    if cv["projects"]:
        pr = cv["projects"][0]
        first = re.split(r"(?<=[.!?])\s", pr["description"] or "")[0].rstrip(".")
        out += ["", f"Outside of my main role, I built {pr['name']}" + (f" — {lower_first(first)}." if first else ".")]

    out += ["", f"I would welcome the opportunity to discuss how my background can support {company or 'your team'}. "
                "Thank you for your time and consideration.", "", "Kind regards,", p.get("full_name") or "Candidate"]
    contact = " | ".join(x for x in [p.get("email"), p.get("phone")] if x)
    if contact:
        out.append(contact)
    return "\n".join(out)


def mock_tailored(cv, job):
    result = analyze(all_cv_text(cv), job)
    job_terms = set(result["matched"]) | set(result["missing"])

    def relevance(text):
        return len(set(keyword_counts(text)) & job_terms)

    out = ["TAILORED CV DRAFT", "=" * 40, "", "PROFESSIONAL SUMMARY",
           mock_summary(cv, prefer=result["matched"]), ""]

    if cv["skills"]:
        out += ["MOST RELEVANT SKILLS", ", ".join(top_skills(cv, 12, result["matched"])), ""]

    if cv["experience"]:
        out.append("EXPERIENCE (ordered by relevance to this job)")
        for x in sorted(cv["experience"], key=lambda x: -relevance(" ".join(str(v) for v in x.values()))):
            out += ["", f"{x['position']} — {x['company']} ({tpl.date_range(x['start_date'], x['end_date'])})",
                    polish_bullets(x["responsibilities"])]
            if x.get("achievements"):
                out.append(polish_bullets(x["achievements"]))
        out.append("")

    if cv["projects"]:
        out.append("RELEVANT PROJECTS")
        for x in sorted(cv["projects"], key=lambda x: -relevance(" ".join(str(v) for v in x.values()))):
            out.append(f"• {x['name']}: {x['description']}")
        out.append("")

    out += [f"Keyword match indicator: {result['score']}%"]
    if result["missing"]:
        out += ["", "KEYWORDS TO REVIEW (add only if they genuinely apply to you):",
                ", ".join(result["missing"][:12])]
    return "\n".join(out)


def mock_ai(feature, ctx):
    text = ctx.get("text", "")
    if feature == "summary":
        return mock_summary(ctx["cv"], text)
    if feature == "experience":
        return polish_bullets(text)
    if feature == "project":
        return mock_project(text)
    if feature == "cover":
        return mock_cover(ctx["cv"], ctx["job_title"], ctx.get("company", ""), ctx.get("job", ""))
    if feature == "tailored":
        return mock_tailored(ctx["cv"], ctx["job"])
    return "No AI result generated."


def generate_ai(feature, prompt, ctx):
    if ai_online():
        with st.spinner(f"Thinking with {ai_model()}…"):
            result = ollama(prompt)
        if result:
            return result, f"Ollama local AI ({ai_model()})"
        return mock_ai(feature, ctx), "Offline smart engine (Ollama request failed)"
    return mock_ai(feature, ctx), "Offline smart engine"


def ai_polish(text, kind):
    if not (text or "").strip():
        return text
    feature = "experience" if kind == "experience" else "project"
    prompt = (
        "Rewrite the following into 3-5 concise, ATS-friendly CV bullet points, one per line, each starting with '• ' "
        "and a strong action verb. Preserve every fact and number. Do not invent anything. Output only the bullets.\n\n"
        f"{text}"
    )
    result, _ = generate_ai(feature, prompt, {"text": text})
    return result


# ============================================================
# ATS ANALYSIS
# ============================================================

STOPWORDS = set("""
the and for with that this from are you your our will have has into about their they them role work using
required requirements candidate candidates team must should can to of in on a an is be as or at by we us it its
was were been being do does did per via able ability strong skills skill knowledge working looking join
opportunity opportunities responsibilities responsibility including within across excellent good great plus
preferred etc based new well also other such more who what which when where how all any both each few most
some than too very just not only own same so but if who whom why while would could may might shall upon
experience experienced years year day days time full part company position job apply salary benefits
environment business help make ensure provide demonstrated proven understanding related relevant level
highly key make making like want wants need needs please get one two three first ideal successful
skilled seeking seek hire hiring hands-on
""".split())

SHORT_TERMS = {"ai", "ml", "bi", "ui", "ux", "qa", "go", "r", "c", "hr", "pr", "seo", "aws", "gcp", "sql", "api"}

PHRASES = [
    "machine learning", "deep learning", "data analysis", "data analytics", "data science",
    "data visualization", "data engineering", "big data", "project management",
    "product management", "computer vision", "natural language processing", "power bi", "google analytics",
    "customer service", "problem solving", "unit testing", "version control", "rest api", "ci/cd",
    "cloud computing", "stakeholder management", "time management", "business intelligence",
    "front end", "back end", "full stack", "user experience", "attention to detail", "software development",
    "quality assurance", "digital marketing", "financial analysis", "supply chain", "social media",
    "team leadership", "spring boot", "react native", "sql server", "microsoft excel", "a/b testing",
    "content writing", "data modeling", "statistical analysis", "web development",
]

# British -> American spellings so "visualisation" matches "visualization"
SPELLING = [(r"isation", "ization"), (r"analys(e|ed|es|ing)\b", r"analyz\1"), (r"modelling", "modeling")]


def normalize(word):
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def keyword_counts(text):
    low = (text or "").lower()
    for pattern, repl in SPELLING:
        low = re.sub(pattern, repl, low)
    counts = Counter()
    for ph in PHRASES:
        pattern = r"(?<![a-z])" + re.escape(ph) + r"(?![a-z])"
        n = len(re.findall(pattern, low))
        if n:
            counts[ph] += n * 2
            low = re.sub(pattern, " ", low)  # don't also count "power" and "bi"
    for w in re.findall(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]", low):
        if w in STOPWORDS or (len(w) < 3 and w not in SHORT_TERMS):
            continue
        w = normalize(w)
        if w not in STOPWORDS:
            counts[w] += 1
    return counts


def keywords_ranked(text):
    return [k for k, _ in keyword_counts(text).most_common()]


def analyze(cv_text, job, top_n=35):
    job_counts = dict(keyword_counts(job).most_common(top_n))
    cv_terms = set(keyword_counts(cv_text))
    matched = [k for k in job_counts if k in cv_terms]
    missing = [k for k in job_counts if k not in cv_terms]
    total = sum(job_counts.values())
    score = round(sum(job_counts[k] for k in matched) / total * 100, 1) if total else 0
    return {"score": score, "matched": matched, "missing": missing}


def cv_checks(cv):
    p = cv["profile"]
    summary_words = len((p.get("summary") or "").split())
    work_text = " ".join(f"{x['responsibilities'] or ''} {x['achievements'] or ''}" for x in cv["experience"])
    return [
        {"ok": bool(p.get("full_name") and p.get("title")), "label": "Name and professional title",
         "tip": "Add both in CV Builder → Personal."},
        {"ok": bool(p.get("email") and p.get("phone")), "label": "Email and phone number",
         "tip": "Recruiters need at least two ways to reach you."},
        {"ok": 30 <= summary_words <= 120, "label": f"Summary length ({summary_words} words)",
         "tip": "Aim for 30–120 words. Use 'Write my summary' in CV Builder."},
        {"ok": bool(cv["experience"]), "label": "At least one experience entry",
         "tip": "Include internships, freelance or volunteer roles too."},
        {"ok": bool(re.search(r"\d", work_text)), "label": "Quantified achievements",
         "tip": "Numbers (%, £, hours saved, users) make impact measurable."},
        {"ok": len(cv["skills"]) >= 6, "label": f"6+ skills listed ({len(cv['skills'])})",
         "tip": "Mix technical tools and soft skills."},
        {"ok": bool(cv["education"]), "label": "Education added", "tip": "Add your highest qualification."},
        {"ok": bool(cv["projects"]), "label": "Projects showcased", "tip": "Projects prove skills in practice."},
        {"ok": bool(p.get("linkedin") or p.get("github") or p.get("portfolio")), "label": "Professional links",
         "tip": "Add LinkedIn, GitHub or a portfolio URL."},
    ]


def cv_strength(cv):
    checks = cv_checks(cv)
    return round(sum(c["ok"] for c in checks) / len(checks) * 100)


# ============================================================
# UI HELPERS
# ============================================================

def html_block(markup):
    st.markdown(markup, unsafe_allow_html=True)


def page_header(eyebrow, title, subtitle=""):
    html_block(fx.header_html(eyebrow, title, subtitle))


def chips(items, kind=""):
    html_block(fx.chips_html(items, kind) or "<span class='cf-chip'>None</span>")


def flash(message, icon="✅"):
    st.session_state["flash"] = (message, icon)


def show_flash():
    if "flash" in st.session_state:
        message, icon = st.session_state.pop("flash")
        st.toast(message, icon=icon)


def empty_state(message):
    html_block(f"<div class='cf-check'><span class='ic no'>i</span><span>{fx.esc(message)}</span></div>")


def cv_has_data(cv):
    return bool(cv["profile"]["full_name"] or any(cv[t] for t in ENTRY_TABLES))


# ============================================================
# ENTRY EDITOR (education, experience, projects, certifications)
# ============================================================

SECTIONS = {
    "education": {
        "noun": "education",
        "fields": [("degree", "Degree / qualification", "text"), ("institution", "School or university", "text"),
                   ("start_year", "Start year", "text"), ("end_year", "End year", "text"),
                   ("grade", "CGPA / grade", "text"), ("description", "Description", "area")],
        "required": "degree",
        "title": lambda x: x["degree"],
        "subtitle": lambda x: " · ".join(v for v in [x["institution"], tpl.date_range(x["start_year"], x["end_year"]), x["grade"]] if v),
        "body": lambda x: x["description"],
    },
    "experience": {
        "noun": "position",
        "fields": [("position", "Job title", "text"), ("company", "Employer", "text"),
                   ("location", "City", "text"), ("start_date", "Start date", "text"),
                   ("end_date", "End date (or Present)", "text"),
                   ("responsibilities", "Responsibilities — one per line", "area"),
                   ("achievements", "Achievements — one per line, include numbers", "area")],
        "required": "position",
        "polish": ["responsibilities", "achievements"],
        "title": lambda x: f"{x['position']} — {x['company']}" if x["company"] else x["position"],
        "subtitle": lambda x: " · ".join(v for v in [x["location"], tpl.date_range(x["start_date"], x["end_date"])] if v),
        "body": lambda x: x["responsibilities"],
    },
    "projects": {
        "noun": "project",
        "fields": [("name", "Project name", "text"), ("technologies", "Technologies (comma-separated)", "text"),
                   ("github_url", "Code URL", "text"), ("demo_url", "Live demo URL", "text"),
                   ("description", "Description", "area")],
        "required": "name",
        "polish": ["description"],
        "title": lambda x: x["name"],
        "subtitle": lambda x: x["technologies"],
        "body": lambda x: x["description"],
    },
    "certifications": {
        "noun": "certificate",
        "fields": [("name", "Certificate name", "text"), ("organization", "Issued by", "text"),
                   ("date", "Date", "text"), ("credential_url", "Credential URL", "text")],
        "required": "name",
        "title": lambda x: x["name"],
        "subtitle": lambda x: " · ".join(v for v in [x["organization"], x["date"]] if v),
        "body": lambda x: x["credential_url"],
    },
}


def render_fields(spec, values, prefix):
    out = {}
    texts = [f for f in spec["fields"] if f[2] == "text"]
    areas = [f for f in spec["fields"] if f[2] == "area"]
    cols = st.columns(2)
    for i, (key, label, _) in enumerate(texts):
        out[key] = cols[i % 2].text_input(label, values.get(key) or "", key=f"{prefix}_{key}")
    for key, label, _ in areas:
        out[key] = st.text_area(label, values.get(key) or "", key=f"{prefix}_{key}", height=110)
    return out


def apply_polish(spec, values):
    for field in spec.get("polish", []):
        values[field] = ai_polish(values[field], "project" if field == "description" else "experience")
    return values


def entry_editor(table):
    spec = SECTIONS[table]
    items = rows(table)
    polishable = bool(spec.get("polish"))

    for i, x in enumerate(items):
        with st.container(key=f"card_{table}_{x['id']}"):
            if st.session_state.get("editing") == (table, x["id"]):
                with st.form(f"edit_{table}_{x['id']}", border=False):
                    values = render_fields(spec, x, f"edit_{table}_{x['id']}")
                    with st.container(horizontal=True):
                        save = st.form_submit_button("Save", type="primary", icon=":material/check:")
                        polish = st.form_submit_button("Polish with AI & save", icon=":material/auto_awesome:") if polishable else False
                        cancel = st.form_submit_button("Cancel", type="tertiary")
                if save or polish:
                    update_row(table, x["id"], apply_polish(spec, values) if polish else values)
                    st.session_state.pop("editing", None)
                    flash("Changes saved")
                    st.rerun()
                if cancel:
                    st.session_state.pop("editing", None)
                    st.rerun()
                continue

            text, menu = st.columns([14, 1])
            text.markdown(fx.entry_html(spec["title"](x), spec["subtitle"](x), spec["body"](x) or ""),
                          unsafe_allow_html=True)
            with menu.popover("", icon=":material/more_vert:", type="tertiary", help="Options"):
                if st.button("Edit", icon=":material/edit:", key=f"ed_{table}_{x['id']}", type="tertiary"):
                    st.session_state["editing"] = (table, x["id"])
                    st.rerun()
                if i > 0 and st.button("Move up", icon=":material/arrow_upward:", key=f"up_{table}_{x['id']}", type="tertiary"):
                    move_row(table, x["id"], -1)
                    st.rerun()
                if i < len(items) - 1 and st.button("Move down", icon=":material/arrow_downward:",
                                                    key=f"dn_{table}_{x['id']}", type="tertiary"):
                    move_row(table, x["id"], 1)
                    st.rerun()
                if st.button("Delete", icon=":material/delete:", key=f"del_{table}_{x['id']}", type="tertiary"):
                    delete_row(table, x["id"])
                    flash("Entry deleted", "🗑️")
                    st.rerun()

    with st.expander(f"Add {spec['noun']}", icon=":material/add:", expanded=not items):
        with st.form(f"add_{table}", clear_on_submit=True, border=False):
            values = render_fields(spec, {}, f"add_{table}")
            with st.container(horizontal=True):
                save = st.form_submit_button(f"Add {spec['noun']}", type="primary", icon=":material/add:")
                polish = st.form_submit_button("Polish with AI & add", icon=":material/auto_awesome:") if polishable else False
        if save or polish:
            if not values[spec["required"]].strip():
                st.warning("Please fill in the first field.")
            else:
                insert_row(table, apply_polish(spec, values) if polish else values)
                flash("Added to your CV")
                st.rerun()


# ============================================================
# CV BUILDER (step by step, live preview)
# ============================================================

STEPS = [
    ("personal", "Personal", "Personal details", "How employers will contact you, plus a short professional summary."),
    ("experience", "Experience", "Work experience", "Most recent first. One responsibility per line; polish rough notes with AI."),
    ("education", "Education", "Education & training", "Degrees, diplomas and relevant courses."),
    ("skills", "Skills", "Skills", "Add several at once, separated by commas, and set your proficiency."),
    ("projects", "Projects", "Projects", "Show what you have built. Links appear on your website CV."),
    ("certifications", "Certificates", "Certificates", "Licences, courses and credentials."),
    ("finish", "Finish", "Review & download", "Check your CV strength, then download or publish it."),
]
STEP_KEYS = [s[0] for s in STEPS]


def set_step(key):
    st.session_state["step"] = key
    st.session_state.pop("editing", None)


def step_done(key, cv):
    if key == "personal":
        return bool(cv["profile"]["full_name"] and cv["profile"]["email"])
    if key == "finish":
        return cv_strength(cv) == 100
    return bool(cv[key])


def step_personal():
    p = get_profile()
    photo = photo_abs(p.get("photo_path"))

    with st.container(key="card_photo"):
        a, b = st.columns([1, 3.2], vertical_alignment="center")
        with a:
            if photo:
                st.image(photo, width=96)
            else:
                html_block(
                    "<div style='width:96px;aspect-ratio:1;border-radius:20px;display:grid;place-items:center;font-size:32px;"
                    "font-weight:800;color:#fff;font-family:Plus Jakarta Sans;background:var(--brand)'>"
                    f"{fx.esc(tpl.initials(p['full_name']))}</div>")
        with b:
            upload = st.file_uploader("Profile photo (optional)", type=["png", "jpg", "jpeg", "webp"])
            with st.container(horizontal=True):
                if upload and st.button("Save photo", type="primary", icon=":material/upload:"):
                    ext = Path(upload.name).suffix.lower()
                    for old in PHOTO_DIR.glob("profile.*"):
                        old.unlink(missing_ok=True)
                    target = PHOTO_DIR / f"profile{ext}"
                    target.write_bytes(upload.getvalue())
                    update_profile_field("photo_path", str(target.relative_to(BASE_DIR)))
                    flash("Photo saved")
                    st.rerun()
                if photo and st.button("Remove photo", type="tertiary", icon=":material/close:"):
                    Path(photo).unlink(missing_ok=True)
                    update_profile_field("photo_path", "")
                    st.rerun()

    with st.form("profile_form"):
        c1, c2 = st.columns(2)
        full_name = c1.text_input("Full name", p["full_name"])
        title = c2.text_input("Professional title", p["title"], placeholder="e.g. Data Analyst")
        email = c1.text_input("Email", p["email"])
        phone = c2.text_input("Phone", p["phone"])
        location = c1.text_input("City, country", p["location"])
        linkedin = c2.text_input("LinkedIn", p["linkedin"])
        github = c1.text_input("GitHub", p["github"])
        portfolio = c2.text_input("Website / portfolio", p["portfolio"])
        summary = st.text_area("Professional summary", p["summary"], height=150,
                               help="30–120 words. Leave blank and use 'Write it for me' below.")
        submitted = st.form_submit_button("Save details", type="primary", icon=":material/check:")

    if submitted:
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
            st.warning("The email address looks invalid.")
        else:
            save_profile({
                "full_name": full_name.strip(), "title": title.strip(), "email": email.strip(),
                "phone": phone.strip(), "location": location.strip(), "linkedin": linkedin.strip(),
                "github": github.strip(), "portfolio": portfolio.strip(), "summary": summary.strip(),
                "photo_path": p["photo_path"],
            })
            flash("Details saved")
            st.rerun()

    if st.button("Write my summary from my saved CV", icon=":material/auto_awesome:", type="tertiary"):
        cv = load_cv()
        prompt = ("Write a concise ATS-friendly professional summary (50-90 words) in third person without pronouns. "
                  "Use ONLY these facts; never invent experience, numbers or qualifications.\n\n" + all_cv_text(cv))
        result, provider = generate_ai("summary", prompt, {"cv": cv})
        update_profile_field("summary", result)
        flash(f"Summary written with {provider}. Please review it.", "✨")
        st.rerun()


def step_skills():
    with st.form("skill_form", clear_on_submit=True):
        names = st.text_input("Skills", placeholder="e.g. Python, SQL, Project management")
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", SKILL_CATEGORIES)
        level = c2.select_slider("Proficiency", options=list(LEVELS), value=3, format_func=LEVELS.get)
        add = st.form_submit_button("Add skills", type="primary", icon=":material/add:")

    if add:
        existing = {s["skill_name"].lower() for s in rows("skills")}
        added = 0
        for name in (n.strip() for n in names.split(",")):
            if name and name.lower() not in existing:
                insert_row("skills", {"skill_name": name, "category": category, "level": level})
                existing.add(name.lower())
                added += 1
        if added:
            flash(f"Added {added} skill(s)")
            st.rerun()
        st.warning("No new skills to add (empty or already listed).")

    skills = rows("skills")
    for cat in SKILL_CATEGORIES:
        group = [s for s in skills if (s["category"] or "Other") == cat]
        if not group:
            continue
        html_block(f"<div class='cf-eyebrow' style='margin:1rem 0 .4rem'>{fx.esc(cat)}</div>")
        cols = st.columns(2)
        for i, s in enumerate(group):
            level = int(s.get("level") or 3)
            with cols[i % 2].container(key=f"card_skill_{s['id']}"):
                a, b = st.columns([6, 1], vertical_alignment="center")
                a.markdown(f"<div class='cf-skill'>{fx.esc(s['skill_name'])}{fx.dots_html(level)}</div>",
                           unsafe_allow_html=True)
                if b.button("", icon=":material/close:", key=f"skill{s['id']}", type="tertiary", help="Remove"):
                    delete_row("skills", s["id"])
                    st.rerun()


def export_buttons(cv, template):
    cv_html = tpl.build_cv_html(cv, template, theme_accent(), toolbar=True)
    name = re.sub(r"[^A-Za-z0-9]+", "_", cv["profile"]["full_name"] or "cv").strip("_") or "cv"
    with st.container(horizontal=True):
        st.download_button("Download CV (HTML → PDF)", cv_html, file_name=f"{name}_CV.html", mime="text/html",
                           type="primary", icon=":material/download:")
        st.download_button("Markdown", tpl.cv_markdown(cv), file_name=f"{name}_CV.md", mime="text/markdown",
                           icon=":material/description:")
        st.download_button("JSON backup", json.dumps(export_data(), indent=2), file_name=f"{name}_smartxcv.json",
                           mime="application/json", icon=":material/data_object:")
    st.caption("Open the HTML file and press Print / Save as PDF for a perfectly formatted A4 PDF.")


def step_finish():
    cv = load_cv()
    score = cv_strength(cv)
    with st.container(key="card_finish"):
        a, b = st.columns([1, 1.6], vertical_alignment="center")
        with a:
            st.iframe(fx.gauge(score, "CV strength", size=150), height=170)
        with b:
            html_block(fx.checklist_html([c for c in cv_checks(cv) if not c["ok"]][:4]
                                         or [{"ok": True, "label": "Your CV is complete — great work!", "tip": ""}]))
    st.write("")
    export_buttons(cv, current_template())
    st.write("")
    with st.container(horizontal=True):
        st.page_link(PAGE["design"], label="Change design", icon=":material/palette:")
        st.page_link(PAGE["digital"], label="Publish as website", icon=":material/language:")
        st.page_link(PAGE["ai"], label="Tailor to a job", icon=":material/auto_awesome:")


def live_preview():
    cv = load_cv()
    current = current_template()
    a, b = st.columns([2, 1], vertical_alignment="center")
    chosen = a.selectbox("Template", list(tpl.TEMPLATES), index=list(tpl.TEMPLATES).index(current),
                         label_visibility="collapsed", key="live_tpl")
    if chosen != current:
        set_setting("template", chosen)
    b.page_link(PAGE["design"], label="Design", icon=":material/palette:")
    st.iframe(tpl.build_cv_html(cv, chosen, theme_accent(), fit=True), height=800)


STEP_RENDER = {
    "personal": step_personal,
    "skills": step_skills,
    "finish": step_finish,
}


def page_builder():
    cv = load_cv()
    step = st.session_state.setdefault("step", "personal")
    idx = STEP_KEYS.index(step)
    _, _, title, subtitle = STEPS[idx]

    with st.container(horizontal=True, key="stepper", gap="small"):
        for n, (key, label, _, _) in enumerate(STEPS):
            mark = "✓ " if step_done(key, cv) and key != step else f"{n + 1}  "
            st.button(f"{mark}{label}", key=f"step_{key}", type="primary" if key == step else "secondary",
                      on_click=set_step, args=(key,))
    html_block(fx.steps_line_html(idx, len(STEPS)))
    show_flash()

    left, right = st.columns([1.08, 1], gap="large")
    with left:
        page_header(f"Step {idx + 1} of {len(STEPS)}", title, subtitle)
        STEP_RENDER.get(step, lambda: entry_editor(step))()
        st.write("")
        with st.container(horizontal=True, horizontal_alignment="distribute" if idx > 0 else "right"):
            if idx > 0:
                st.button("Back", icon=":material/arrow_back:", on_click=set_step, args=(STEP_KEYS[idx - 1],))
            if idx < len(STEPS) - 1:
                st.button(f"Next: {STEPS[idx + 1][1]}", type="primary", icon=":material/arrow_forward:",
                          icon_position="right", on_click=set_step, args=(STEP_KEYS[idx + 1],))
    with right:
        with st.container(key="preview"):
            live_preview()


# ============================================================
# HOME
# ============================================================

def page_home():
    cv = load_cv()
    p = cv["profile"]
    score = cv_strength(cv)
    accent = theme_accent()
    current = current_template()
    show_flash()

    left, right = st.columns([1, 1.05], gap="large", vertical_alignment="center")
    with left:
        first = (p["full_name"] or "").split(" ")[0]
        html_block(fx.hero_text_html(
            "AI CV builder",
            f"Welcome back, {first}." if first else "Build a CV that",
            "Let's land your next role." if first else "gets you hired.",
            "Create an ATS-friendly CV step by step, tailor it to any job with private local AI, "
            "and publish it as your own website. Free, forever.",
        ))
        with st.container(horizontal=True):
            with st.container(key="cta", width="content"):
                st.page_link(PAGE["builder"], label="Continue my CV" if cv_has_data(cv) else "Create my CV",
                             icon=":material/arrow_forward:", icon_position="right")
            with st.container(key="cta2", width="content"):
                st.page_link(PAGE["design"], label="Download", icon=":material/download:")
        if not cv_has_data(cv) and st.button("Or explore with a demo CV", icon=":material/auto_awesome:", type="tertiary"):
            import_data(DEMO_DATA)
            flash("Demo CV loaded")
            st.rerun()
        html_block("<div class='cf-trust'><span>ATS-friendly templates</span><span>Private local AI</span>"
                   "<span>Free PDF export</span></div>")

    with right:
        order = [current] + [t for t in tpl.TEMPLATES if t != current][:2]
        pages = [tpl.build_cv_html(cv, t, accent) for t in order]
        st.iframe(fx.hero_3d(pages, accent, score, current), height=560)

    st.write("")
    page_header("Overview", "Your CV at a glance")
    a, b, c = st.columns(3, gap="medium")
    with a.container(key="card_strength", height=330):
        st.markdown("**CV strength**")
        st.iframe(fx.gauge(score, "complete", size=150), height=170)
        passed = sum(x["ok"] for x in cv_checks(cv))
        st.caption(f"{passed} of {len(cv_checks(cv))} checks passed")
        st.page_link(PAGE["builder"], label="Improve my CV", icon=":material/arrow_forward:")
    with b.container(key="card_next", height=330):
        st.markdown("**Next steps**")
        todo = [x for x in cv_checks(cv) if not x["ok"]][:4]
        html_block(fx.checklist_html(todo or [{"ok": True, "label": "Everything looks great", "tip": ""}]))
    with c.container(key="card_scans", height=330):
        st.markdown("**Recent job matches**")
        scans = rows("analyses")[:4]
        if scans:
            for s in scans:
                html_block(f"<div class='cf-check'><span class='ic {'ok' if s['match_score'] >= 70 else 'no'}'>"
                           f"{s['match_score']:.0f}</span><span><b>{fx.esc(s['job_title'] or 'Untitled job')}</b>"
                           f"<span class='tip'>{fx.esc(s['created_at'][:10])}</span></span></div>")
        else:
            st.caption("Paste a job description to see how well your CV matches it.")
        st.page_link(PAGE["ai"], label="Match a job", icon=":material/arrow_forward:")

    st.write("")
    page_header("Tools", "Everything you need to apply")
    tools = [
        ("✍️", "AI writer", "Turn rough notes into strong, factual CV content.", "ai"),
        ("🎯", "Job match", "See matched and missing keywords for any job.", "ai"),
        ("🎨", "Templates", "Four print-ready designs with your brand colour.", "design"),
        ("🌐", "Website CV", "Publish your CV as a personal website.", "digital"),
    ]
    for col, (icon, title, text, key) in zip(st.columns(4, gap="medium"), tools):
        with col.container(key=f"card_tool_{title.replace(' ', '_')}"):
            html_block(fx.tool_html(icon, title, text))
            st.page_link(PAGE[key], label="Open", icon=":material/arrow_forward:", icon_position="right")


# ============================================================
# AI STUDIO
# ============================================================

def tab_writer():
    feature = st.segmented_control(
        "What would you like to write?",
        ["Professional Summary", "Experience Bullets", "Project Description"],
        default="Professional Summary", required=True,
    )
    tone = st.select_slider("Tone", ["Concise", "Professional", "Confident", "Enthusiastic"], value="Professional")
    placeholders = {
        "Professional Summary": "Optional: goals or focus areas. Your saved CV is used automatically.",
        "Experience Bullets": "e.g. I was responsible for weekly sales reports. Worked on a CRM rollout; helped train 12 staff",
        "Project Description": "e.g. Built a Streamlit app that predicts churn. Used scikit-learn. 87% accuracy.",
    }
    text = st.text_area("Your notes", height=170, placeholder=placeholders[feature])

    if st.button("Generate", type="primary", icon=":material/auto_awesome:"):
        cv = load_cv()
        if feature != "Professional Summary" and not text.strip():
            st.warning("Enter some notes first.")
        else:
            facts = f"{text}\n\nCV DATA:\n{all_cv_text(cv)}" if feature == "Professional Summary" else text
            kind, task = {
                "Professional Summary": ("summary", "Write a 50-90 word ATS-friendly professional summary."),
                "Experience Bullets": ("experience", "Rewrite this experience into 3-5 strong CV bullets starting with '• ' and an action verb."),
                "Project Description": ("project", "Write a professional project description: one overview sentence then 2-4 bullets."),
            }[feature]
            prompt = (f"{task} Tone: {tone}. Use ONLY the facts supplied, keep all numbers, "
                      f"never invent experience, results or technologies. Output only the text.\n\n{facts}")
            result, provider = generate_ai(kind, prompt, {"cv": cv, "text": text})
            st.session_state["ai_result"] = {"feature": feature, "text": result, "provider": provider}

    res = st.session_state.get("ai_result")
    if res:
        st.caption(f"Generated with {res['provider']} — edit freely before using it.")
        edited = st.text_area("Result", res["text"], height=220, key=f"ai_out_{hash(res['text'])}")
        with st.container(horizontal=True):
            st.download_button("Download", edited, file_name="smartxcv_ai_result.txt", icon=":material/download:")
            if res["feature"] == "Professional Summary" and st.button("Use as my summary", icon=":material/check:"):
                update_profile_field("summary", edited)
                flash("Summary updated")
                st.rerun()


def tab_match():
    c1, c2 = st.columns(2)
    job_title = c1.text_input("Job title")
    company = c2.text_input("Company (optional)")
    job_description = st.text_area("Job description", height=220, placeholder="Paste the full job advert here…")

    if st.button("Check my match", type="primary", icon=":material/target:"):
        if not job_description.strip():
            st.warning("Paste a job description first.")
        else:
            cv = load_cv()
            result = analyze(all_cv_text(cv), job_description)
            execute("""
                INSERT INTO analyses (job_title, company, job_description, match_score,
                 matched_keywords, missing_keywords, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (job_title, company, job_description, result["score"], json.dumps(result["matched"]),
                  json.dumps(result["missing"]), datetime.now().isoformat(timespec="seconds")))
            st.session_state["ats_result"] = {**result, "job_title": job_title, "checks": cv_checks(cv)}

    res = st.session_state.get("ats_result")
    if not res:
        st.caption("This is a keyword-match indicator for guidance, not a real employer's ATS score.")
        return

    st.write("")
    with st.container(key="card_match"):
        g, info = st.columns([1, 2.2], gap="large", vertical_alignment="center")
        with g:
            st.iframe(fx.gauge(res["score"], "match", size=150), height=170)
        with info:
            verdict = ("Strong match — tailor your summary and apply." if res["score"] >= 70 else
                       "Partial match — add the missing keywords you genuinely have." if res["score"] >= 45 else
                       "Low match — this role may need skills not yet on your CV.")
            st.markdown(f"#### {res['job_title'] or 'This job'}")
            st.caption(verdict)
            st.markdown(f"**Matched · {len(res['matched'])}**")
            chips(res["matched"], "ok")
            st.markdown(f"**Missing · {len(res['missing'])}**")
            chips(res["missing"], "miss")

    if res["missing"]:
        with st.expander("Add missing keywords you genuinely have", icon=":material/add:"):
            pick = st.multiselect("Only select skills you can demonstrate in an interview.", res["missing"])
            cat = st.selectbox("Category", SKILL_CATEGORIES, key="ats_cat")
            if st.button("Add to my skills", disabled=not pick, type="primary"):
                existing = {s["skill_name"].lower() for s in rows("skills")}
                for k in pick:
                    if k.lower() not in existing:
                        insert_row("skills", {"skill_name": k.title() if len(k) > 3 else k.upper(),
                                              "category": cat, "level": 3})
                res["missing"] = [k for k in res["missing"] if k not in pick]
                res["matched"] = res["matched"] + pick
                flash(f"Added {len(pick)} skill(s). Run the check again to update the score.")
                st.rerun()

    with st.expander("CV structure checks", icon=":material/checklist:"):
        html_block(fx.checklist_html(res["checks"]))


def tab_history():
    history = rows("analyses")
    if not history:
        empty_state("No job matches yet.")
        return
    chart = [{"Scan": f"{i + 1:02d}. {h['job_title'] or 'Untitled'}", "Match %": h["match_score"]}
             for i, h in enumerate(reversed(history))]
    st.bar_chart(chart, x="Scan", y="Match %", color=theme_accent(), height=240)
    for h in history:
        with st.container(key=f"card_hist_{h['id']}"):
            a, b, c = st.columns([6, 1, 1], vertical_alignment="center")
            a.markdown(fx.entry_html(h["job_title"] or "Untitled job",
                                     " · ".join(v for v in [h.get("company"), h["created_at"][:16].replace("T", " ")] if v), ""),
                       unsafe_allow_html=True)
            b.markdown(f"<h3 style='margin:0;color:{fx.score_color(h['match_score'])}'>{h['match_score']:.0f}%</h3>",
                       unsafe_allow_html=True)
            if c.button("", icon=":material/delete:", key=f"an{h['id']}", type="tertiary", help="Delete"):
                delete_row("analyses", h["id"])
                st.rerun()


def tab_tailored():
    job = st.text_area("Target job description", height=220, key="tailor_job")
    if st.button("Create tailored draft", type="primary", icon=":material/auto_awesome:"):
        if not job.strip():
            st.warning("Paste a job description first.")
        else:
            cv = load_cv()
            prompt = f"""
Tailor the candidate CV for the job below. Output a plain-text CV draft with sections:
PROFESSIONAL SUMMARY, RELEVANT SKILLS, EXPERIENCE (most relevant first, bullet points), PROJECTS.
Use ONLY genuine information from the CV.
Do not invent skills, employers, qualifications, years or achievements.

JOB:
{job}

CV:
{all_cv_text(cv)}
"""
            st.session_state["tailored"] = generate_ai("tailored", prompt, {"cv": cv, "job": job})

    if "tailored" in st.session_state:
        result, provider = st.session_state["tailored"]
        st.caption(f"Generated with {provider}")
        edited = st.text_area("Tailored draft", result, height=400, key=f"tailored_{hash(result)}")
        st.download_button("Download draft", edited, file_name="tailored_cv.txt", icon=":material/download:")


def tab_cover():
    c1, c2 = st.columns(2)
    job_title = c1.text_input("Job title", key="cover_title")
    company = c2.text_input("Company", key="cover_company")
    job = st.text_area("Job description (optional, improves relevance)", height=180, key="cover_job")

    if st.button("Write cover letter", type="primary", icon=":material/edit_note:"):
        if not job_title.strip():
            st.warning("Enter the job title.")
        else:
            cv = load_cv()
            prompt = f"""
Write a professional cover letter of about 250 words.

Job title: {job_title}
Company: {company}
Job description:
{job}

Candidate CV:
{all_cv_text(cv)}

Use only genuine candidate information. Do not invent qualifications or experience.
Sign off with the candidate's name: {cv['profile']['full_name'] or 'Candidate'}.
"""
            result, provider = generate_ai("cover", prompt, {"cv": cv, "job_title": job_title,
                                                             "company": company, "job": job})
            st.session_state["cover"] = (result, provider, job_title, company)

    if "cover" in st.session_state:
        result, provider, jt, co = st.session_state["cover"]
        st.caption(f"Generated with {provider}")
        edited = st.text_area("Cover letter", result, height=400, key=f"cover_{hash(result)}")
        slug = re.sub(r"[^a-z0-9]+", "_", f"{co or ''} {jt}".lower()).strip("_") or "cover_letter"
        st.download_button("Download letter", edited, file_name=f"cover_letter_{slug}.txt", icon=":material/download:")


def page_ai():
    engine = f"Local AI · {ai_model()}" if ai_online() else "Offline engine"
    page_header("AI studio", "Write, match and tailor",
                f"Every result uses only facts from your CV. Engine: {engine}.")
    show_flash()
    tabs = st.tabs(["Writer", "Job match", "Match history", "Tailored CV", "Cover letter"])
    for tab, render in zip(tabs, [tab_writer, tab_match, tab_history, tab_tailored, tab_cover]):
        with tab:
            render()


# ============================================================
# DESIGN & DOWNLOAD
# ============================================================

def page_design():
    page_header("Design & download", "Choose your template",
                "Every template is A4, print-ready and filled with your own data.")
    show_flash()
    cv = load_cv()
    current = current_template()

    a, b = st.columns([1, 3], vertical_alignment="bottom")
    accent = a.color_picker("Brand colour", theme_accent())
    if accent != theme_accent():
        set_setting("accent", accent)
        st.rerun()
    with b:
        export_buttons(cv, current)

    st.write("")
    for col, (name, desc) in zip(st.columns(4, gap="medium"), tpl.TEMPLATES.items()):
        with col.container(key=f"card_tpl_{name.replace('-', '_')}"):
            st.iframe(tpl.build_cv_html(cv, name, accent, thumb=True), height=372)
            st.markdown(f"**{name}**")
            st.caption(desc)
            if name == current:
                st.button("Selected", key=f"tpl_{name}", icon=":material/check:", disabled=True, width="stretch")
            elif st.button("Use this template", key=f"tpl_{name}", type="primary", width="stretch"):
                set_setting("template", name)
                flash(f"{name} template selected")
                st.rerun()

    st.write("")
    page_header("Preview", f"{current} template")
    st.iframe(tpl.build_cv_html(cv, current, accent, toolbar=True), height=1180)


# ============================================================
# WEBSITE CV
# ============================================================

def page_digital():
    page_header("Website CV", "Your CV as a personal website",
                "Download index.html and host it free on GitHub Pages or Netlify. Scroll the preview to see it animate.")
    cv = load_cv()
    data = {k: cv[k] for k in ENTRY_TABLES}
    data["profile"] = {k: cv["profile"].get(k, "") for k in PROFILE_FIELDS}
    data["photo"] = tpl.photo_data_uri(cv["profile"]["photo_abs"])
    data["accent"] = theme_accent()
    site = fx.digital_cv(data)
    st.download_button("Download website (index.html)", site, file_name="index.html", mime="text/html",
                       type="primary", icon=":material/download:")
    st.write("")
    st.iframe(site, height=1300)


# ============================================================
# SETTINGS
# ============================================================

def page_settings():
    page_header("Settings", "Settings", "Local AI, backups and data.")
    show_flash()
    tab_ai, tab_data = st.tabs(["Local AI", "Data"])

    with tab_ai:
        online = ai_online()
        with st.container(horizontal=True, vertical_alignment="center"):
            if online:
                st.success(f"Ollama is running at {OLLAMA_URL.rsplit('/api/', 1)[0]}")
            else:
                st.info("Ollama is not running. SmartxCV uses its free offline engine.")
            if st.button("Re-check", icon=":material/refresh:"):
                ai_online(refresh=True)
                st.rerun()

        models = st.session_state.get("ai_models", [])
        if models:
            current = ai_model()
            options = models if current in models else [current] + models
            chosen = st.selectbox("Model", options, index=options.index(current))
            if chosen != current:
                set_setting("ollama_model", chosen)
                flash(f"Model set to {chosen}")
                st.rerun()
        else:
            st.code(f"Model: {ai_model()}\nURL:   {OLLAMA_URL}")
            st.caption("Install Ollama from ollama.com, then run:  ollama pull llama3.2")

        if st.button("Test AI"):
            result = ollama("Reply with exactly: SmartxCV local AI is working.") if online else None
            if result:
                st.success(result)
            else:
                st.error("No response from Ollama. The offline engine will be used.")

    with tab_data:
        st.markdown("#### Backup & restore")
        st.download_button("Export JSON backup", json.dumps(export_data(), indent=2),
                           file_name="smartxcv_backup.json", mime="application/json", icon=":material/download:")
        up = st.file_uploader("Restore from a JSON backup", type=["json"])
        if up and st.button("Restore backup (replaces current data)", type="primary"):
            try:
                import_data(json.loads(up.getvalue().decode("utf-8")))
                flash("Backup restored")
                st.rerun()
            except (ValueError, UnicodeDecodeError) as exc:
                st.error(f"Could not restore: {exc}")

        st.divider()
        st.markdown("#### Demo data")
        st.caption("Replaces your current CV with a realistic sample.")
        if st.button("Load demo CV", icon=":material/auto_awesome:"):
            import_data(DEMO_DATA)
            flash("Demo CV loaded")
            st.rerun()

        st.divider()
        st.markdown("#### Danger zone")
        st.caption(f"Database: {DB_PATH}")
        confirm = st.checkbox("I understand this permanently deletes all CV data, photos and job matches.")
        if st.button("Clear all CV data", disabled=not confirm, icon=":material/delete:"):
            clear_all_data()
            for key in ("ats_result", "ai_result", "tailored", "cover"):
                st.session_state.pop(key, None)
            flash("All CV data cleared", "🗑️")
            st.rerun()


# ============================================================
# NAVIGATION (top bar + ☰ menu, no sidebar)
# ============================================================

NAV = [
    ("home", page_home, "Home", ":material/home:", "Create"),
    ("builder", page_builder, "CV Builder", ":material/edit_document:", "Create"),
    ("ai", page_ai, "AI Studio", ":material/auto_awesome:", "Tools"),
    ("design", page_design, "Design & Download", ":material/palette:", "Tools"),
    ("digital", page_digital, "Website CV", ":material/language:", "Tools"),
    ("settings", page_settings, "Settings", ":material/settings:", "Account"),
]

PAGE = {
    key: st.Page(fn, title=title, icon=icon, default=True) if key == "home"
    else st.Page(fn, title=title, icon=icon, url_path=key)
    for key, fn, title, icon, _ in NAV
}


def topbar(cv):
    with st.container(key="topbar"):
        a, b = st.columns([1, 1], vertical_alignment="center")
        a.markdown(fx.brand_html(logo_uri()), unsafe_allow_html=True)
        with b.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
            html_block(fx.meter_html(cv_strength(cv)))
            with st.popover("", icon=":material/menu:", help="Menu"):
                group = None
                for key, _, title, icon, section in NAV:
                    if section != group:
                        group = section
                        html_block(f"<div class='cf-menu-label'>{group}</div>")
                    st.page_link(PAGE[key], label=title, icon=icon, width="stretch")
                engine = f"Local AI · {ai_model()}" if ai_online() else "Offline AI engine"
                st.caption(f"● {engine}")


def main():
    st.set_page_config(page_title="SmartxCV", page_icon=str(LOGO_ICON) if LOGO_ICON.is_file() else "📄",
                       layout="wide", initial_sidebar_state="collapsed")
    st.markdown(fx.global_css(theme_accent()), unsafe_allow_html=True)
    if not st.session_state.get("splash_seen") and logo_uri():
        st.session_state["splash_seen"] = True
        st.markdown(fx.splash_html(logo_uri()), unsafe_allow_html=True)
    current = st.navigation(list(PAGE.values()), position="hidden")
    topbar(load_cv())
    current.run()


if __name__ == "__main__":
    main()
