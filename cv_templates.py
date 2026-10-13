"""
SmartxCV - printable CV templates and text exports.

Every builder takes the `cv` dict produced by app.load_cv():
    {"profile": {...}, "education": [...], "experience": [...],
     "skills": [...], "projects": [...], "certifications": [...]}
"""

from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path

TEMPLATES = {
    "ATS-Friendly": "Single column and plain typography. Parses cleanly in applicant tracking systems.",
    "Modern": "Two-column layout with an accent sidebar for photo, contact details and skill levels.",
    "Professional": "Classic serif typography, centred header and refined accent rules.",
    "Minimal": "Generous whitespace with section labels in a quiet left margin.",
}

FONTS = {
    "ATS-Friendly": "Arial, Helvetica, sans-serif",
    "Modern": "'Segoe UI', Helvetica, Arial, sans-serif",
    "Professional": "Georgia, 'Times New Roman', serif",
    "Minimal": "'Helvetica Neue', Helvetica, Arial, sans-serif",
}


# ============================================================
# SMALL HELPERS
# ============================================================

def esc(value):
    return html.escape(str(value or ""))


def photo_data_uri(path):
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def split_lines(text):
    lines = [l.strip().lstrip("•-*–· ").strip() for l in str(text or "").splitlines()]
    return [l for l in lines if l]


def text_block(text):
    """Multi-line text becomes bullets; a single line stays a paragraph."""
    lines = split_lines(text)
    if not lines:
        return ""
    if len(lines) == 1:
        return f"<p>{esc(lines[0])}</p>"
    return "<ul>" + "".join(f"<li>{esc(l)}</li>" for l in lines) + "</ul>"


def date_range(start, end):
    start, end = (start or "").strip(), (end or "").strip()
    return f"{start} – {end}" if start and end else start or end


def meta(*parts):
    return " · ".join(esc(p) for p in parts if p and str(p).strip())


def link_text(url):
    return str(url or "").replace("https://", "").replace("http://", "").rstrip("/")


def contact_items(p):
    items = [p.get("email"), p.get("phone"), p.get("location")]
    items += [link_text(p.get(k)) for k in ("linkedin", "github", "portfolio")]
    return [x for x in items if x]


def initials(name):
    letters = [w[0] for w in str(name or "CV").split() if w]
    return "".join(letters[:2]).upper() or "CV"


# ============================================================
# SHARED SECTION FRAGMENTS
# ============================================================

def fragments(cv):
    p = cv["profile"]
    f = {"summary": f"<p>{esc(p.get('summary'))}</p>" if p.get("summary") else ""}

    f["experience"] = "".join(
        "<div class='item'>"
        f"<div class='item-head'><h3>{esc(x['position'])}</h3>"
        f"<span class='date'>{esc(date_range(x['start_date'], x['end_date']))}</span></div>"
        f"<div class='meta'>{meta(x['company'], x['location'])}</div>"
        f"{text_block(x['responsibilities'])}"
        + (f"<div class='ach'><strong>Key achievements</strong>{text_block(x['achievements'])}</div>"
           if x.get("achievements") else "")
        + "</div>"
        for x in cv["experience"]
    )

    f["education"] = "".join(
        "<div class='item'>"
        f"<div class='item-head'><h3>{esc(x['degree'])}</h3>"
        f"<span class='date'>{esc(date_range(x['start_year'], x['end_year']))}</span></div>"
        f"<div class='meta'>{meta(x['institution'], x['grade'])}</div>"
        f"{text_block(x['description'])}</div>"
        for x in cv["education"]
    )

    f["projects"] = "".join(
        "<div class='item'>"
        f"<div class='item-head'><h3>{esc(x['name'])}</h3>"
        f"<span class='date'>{esc(link_text(x.get('github_url') or x.get('demo_url')))}</span></div>"
        f"{text_block(x['description'])}"
        + (f"<div class='meta'>Technologies: {esc(x['technologies'])}</div>" if x.get("technologies") else "")
        + "</div>"
        for x in cv["projects"]
    )

    f["certifications"] = (
        "<ul>" + "".join(
            f"<li><strong>{esc(x['name'])}</strong>"
            + (f" — {meta(x['organization'], x['date'])}" if x.get("organization") or x.get("date") else "")
            + "</li>"
            for x in cv["certifications"]
        ) + "</ul>"
    ) if cv["certifications"] else ""

    groups = {}
    for s in cv["skills"]:
        groups.setdefault(s.get("category") or "Other", []).append(s)

    f["skills_lines"] = "".join(
        f"<p><strong>{esc(cat)}:</strong> {esc(', '.join(s['skill_name'] for s in items))}</p>"
        for cat, items in groups.items()
    )
    f["skills_chips"] = "".join(
        f"<span class='chip'>{esc(s['skill_name'])}</span>" for s in cv["skills"]
    )
    f["skills_levels"] = "".join(
        f"<div class='lvl'><span>{esc(s['skill_name'])}</span><span class='dots'>"
        + "".join(f"<i class='{'on' if n < int(s.get('level') or 3) else ''}'></i>" for n in range(5))
        + "</span></div>"
        for s in cv["skills"]
    )
    return f


def section(title, body):
    return f"<section><h2>{title}</h2>{body}</section>" if body else ""


def row_section(title, body):
    return f"<section class='row'><h2>{title}</h2><div>{body}</div></section>" if body else ""


MAIN_ORDER = [
    ("Professional Summary", "summary"),
    ("Experience", "experience"),
    ("Projects", "projects"),
    ("Education", "education"),
]


# ============================================================
# CSS
# ============================================================

BASE_CSS = """
*{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;background:#e9ecf2;color:#1f2430;font-family:__FONT__;font-size:13.5px;line-height:1.5}
.page{width:794px;min-height:1123px;margin:28px auto;background:#fff;box-shadow:0 10px 40px rgba(15,23,42,.14)}
h1,h2,h3,p{margin:0}
p+p{margin-top:4px}
ul{margin:6px 0 0;padding-left:18px} li{margin:2px 0}
a{color:inherit;text-decoration:none}
.item{margin-bottom:14px;break-inside:avoid}
.item-head{display:flex;justify-content:space-between;gap:12px;align-items:baseline}
.item h3{font-size:14.5px}
.date{font-size:12px;color:#6b7280;white-space:nowrap}
.meta{font-size:12.5px;color:#6b7280;margin:1px 0 4px}
.ach{margin-top:6px}
.ach strong{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:#4b5563}
.chip{display:inline-block;padding:3px 10px;margin:0 5px 6px 0;border-radius:99px;font-size:12px;border:1px solid #d1d5db}
.toolbar{position:sticky;top:0;z-index:5;display:flex;justify-content:center;gap:10px;padding:10px;background:rgba(233,236,242,.92);backdrop-filter:blur(6px)}
.toolbar button{font:600 13px system-ui,sans-serif;padding:9px 18px;border-radius:10px;border:none;background:__ACCENT__;color:#fff;cursor:pointer}
.toolbar button:hover{filter:brightness(1.1)}
@page{size:A4;margin:0}
@media print{body{background:#fff}.page{margin:0;box-shadow:none;width:auto;min-height:0}.toolbar{display:none}}
@media (max-width:830px){.page{width:auto;margin:0;min-height:0}}
"""

TEMPLATE_CSS = {
    "ATS-Friendly": """
.page{padding:46px 54px}
header{border-bottom:2px solid #111;padding-bottom:12px;margin-bottom:4px}
h1{font-size:28px}
.headline{font-size:15px;color:#374151;margin-top:2px}
.contact{font-size:12.5px;color:#374151;margin-top:6px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.12em;margin:18px 0 8px;border-bottom:1px solid #9ca3af;padding-bottom:3px}
""",
    "Modern": """
.page{display:grid;grid-template-columns:250px 1fr}
aside{background:__ACCENT__;color:#fff;padding:40px 24px}
.photo{width:120px;height:120px;border-radius:50%;object-fit:cover;border:4px solid rgba(255,255,255,.35);display:block;margin:0 auto 18px}
.initials{width:120px;height:120px;border-radius:50%;margin:0 auto 18px;display:flex;align-items:center;justify-content:center;font-size:40px;font-weight:700;background:rgba(255,255,255,.18);border:4px solid rgba(255,255,255,.35)}
aside h2{font-size:12px;text-transform:uppercase;letter-spacing:.14em;margin:22px 0 10px;opacity:.9;border-bottom:1px solid rgba(255,255,255,.3);padding-bottom:4px}
aside .c{font-size:12px;margin-bottom:6px;word-break:break-word}
aside ul{padding-left:16px;font-size:12px}
aside .meta{color:rgba(255,255,255,.75)}
.lvl{display:flex;justify-content:space-between;align-items:center;font-size:12.5px;margin-bottom:6px;gap:8px}
.dots{white-space:nowrap}
.dots i{display:inline-block;width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,.3);margin-left:3px}
.dots i.on{background:#fff}
.main{padding:42px 38px}
h1{font-size:32px;color:__ACCENT__;line-height:1.1}
.headline{font-size:14px;color:#4b5563;margin:6px 0 4px;letter-spacing:.08em;text-transform:uppercase}
.main h2{font-size:15px;color:__ACCENT__;margin:22px 0 10px;display:flex;align-items:center;gap:10px}
.main h2::after{content:"";flex:1;height:2px;background:linear-gradient(90deg,__ACCENT__,transparent)}
""",
    "Professional": """
.page{padding:50px 60px}
header{text-align:center;padding-bottom:14px;border-bottom:3px double __ACCENT__}
h1{font-size:30px;letter-spacing:.06em;text-transform:uppercase}
.headline{font-style:italic;color:#4b5563;font-size:15px;margin-top:4px}
.contact{font-size:12px;margin-top:8px;color:#374151;font-family:Arial,sans-serif}
h2{font-size:13.5px;letter-spacing:.18em;text-transform:uppercase;color:__ACCENT__;margin:22px 0 10px;padding-bottom:4px;border-bottom:1px solid #e5e7eb}
.item h3{font-size:15px}
.chip{border-color:__ACCENT__;color:__ACCENT__}
""",
    "Minimal": """
.page{padding:64px 70px}
h1{font-size:36px;font-weight:300;letter-spacing:-.02em}
h1 b{font-weight:700}
.headline{color:__ACCENT__;font-size:13px;letter-spacing:.2em;text-transform:uppercase;margin-top:8px}
.contact{font-size:12.5px;color:#6b7280;margin-top:12px}
.row{display:grid;grid-template-columns:130px 1fr;gap:24px;margin-top:30px}
.row h2{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#9ca3af;font-weight:600;padding-top:3px}
.chip{border:none;background:#f3f4f6}
""",
}


# ============================================================
# LAYOUTS
# ============================================================

def header_html(p, centered_name=False):
    name = esc(p.get("full_name") or "Your Name")
    if centered_name:
        first, _, rest = name.partition(" ")
        name = f"{first} <b>{rest}</b>" if rest else f"<b>{first}</b>"
    return (
        f"<header><h1>{name}</h1>"
        + (f"<div class='headline'>{esc(p.get('title'))}</div>" if p.get("title") else "")
        + f"<div class='contact'>{' · '.join(esc(c) for c in contact_items(p))}</div></header>"
    )


def layout_single(cv, f, skills_key):
    body = header_html(cv["profile"])
    for title, key in MAIN_ORDER:
        body += section(title, f[key])
    body += section("Skills", f[skills_key])
    body += section("Certifications", f["certifications"])
    return f"<div class='page'>{body}</div>"


def layout_modern(cv, f):
    p = cv["profile"]
    photo = photo_data_uri(p.get("photo_abs"))
    avatar = (f"<img class='photo' src='{photo}' alt=''>" if photo
              else f"<div class='initials'>{esc(initials(p.get('full_name')))}</div>")
    contact = "".join(f"<div class='c'>{esc(c)}</div>" for c in contact_items(p))
    aside = (
        avatar
        + section("Contact", contact)
        + section("Skills", f["skills_levels"])
        + section("Certifications", f["certifications"])
    )
    main = (
        f"<h1>{esc(p.get('full_name') or 'Your Name')}</h1>"
        + (f"<div class='headline'>{esc(p.get('title'))}</div>" if p.get("title") else "")
        + "".join(section(t, f[k]) for t, k in MAIN_ORDER)
    )
    return f"<div class='page'><aside>{aside}</aside><div class='main'>{main}</div></div>"


def layout_minimal(cv, f):
    body = header_html(cv["profile"], centered_name=True)
    body += row_section("Profile", f["summary"])
    body += row_section("Experience", f["experience"])
    body += row_section("Projects", f["projects"])
    body += row_section("Education", f["education"])
    body += row_section("Skills", f["skills_chips"])
    body += row_section("Certificates", f["certifications"])
    return f"<div class='page'>{body}</div>"


FIT_JS = ("<script>function f(){document.documentElement.style.zoom=Math.min(1,(innerWidth-28)/794)}"
          "f();addEventListener('resize',f)</script>")


def build_cv_html(cv, template="ATS-Friendly", accent="#2563eb", toolbar=False, thumb=False, fit=False):
    template = template if template in TEMPLATES else "ATS-Friendly"
    f = fragments(cv)

    if template == "Modern":
        page = layout_modern(cv, f)
    elif template == "Minimal":
        page = layout_minimal(cv, f)
    elif template == "Professional":
        page = layout_single(cv, f, "skills_chips")
    else:
        page = layout_single(cv, f, "skills_lines")

    css = (BASE_CSS + TEMPLATE_CSS[template]).replace("__FONT__", FONTS[template]).replace("__ACCENT__", accent)
    if thumb:
        css += "html{zoom:.33;overflow:hidden}.page{margin:0 auto;box-shadow:none}body{background:#fff}"
    if fit:
        css += ("body{background:#eef1f6}.page{margin:14px auto;box-shadow:0 2px 6px rgba(15,23,42,.06),"
                "0 18px 40px -18px rgba(15,23,42,.25)}")

    bar = ("<div class='toolbar'><button onclick='window.print()'>🖨️ Print / Save as PDF</button></div>"
           if toolbar else "")

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(cv['profile'].get('full_name') or 'CV')} - CV</title>"
        f"<style>{css}</style></head><body>{bar}{page}{FIT_JS if fit else ''}</body></html>"
    )


# ============================================================
# TEXT EXPORTS
# ============================================================

def cv_markdown(cv):
    p = cv["profile"]
    out = [f"# {p.get('full_name') or 'Your Name'}"]
    if p.get("title"):
        out.append(f"**{p['title']}**")
    out.append(" · ".join(contact_items(p)))

    if p.get("summary"):
        out += ["", "## Professional Summary", p["summary"]]

    if cv["experience"]:
        out += ["", "## Experience"]
        for x in cv["experience"]:
            out += ["", f"### {x['position']} — {x['company']}",
                    f"*{meta(x['location'], date_range(x['start_date'], x['end_date']))}*"]
            out += [f"- {l}" for l in split_lines(x["responsibilities"])]
            out += [f"- **Achievement:** {l}" for l in split_lines(x["achievements"])]

    if cv["projects"]:
        out += ["", "## Projects"]
        for x in cv["projects"]:
            out += ["", f"### {x['name']}", x["description"] or ""]
            if x.get("technologies"):
                out.append(f"*Technologies: {x['technologies']}*")

    if cv["education"]:
        out += ["", "## Education"]
        for x in cv["education"]:
            out += ["", f"### {x['degree']} — {x['institution']}",
                    f"*{meta(date_range(x['start_year'], x['end_year']), x['grade'])}*"]
            if x.get("description"):
                out.append(x["description"])

    if cv["skills"]:
        groups = {}
        for s in cv["skills"]:
            groups.setdefault(s.get("category") or "Other", []).append(s["skill_name"])
        out += ["", "## Skills"] + [f"- **{c}:** {', '.join(v)}" for c, v in groups.items()]

    if cv["certifications"]:
        out += ["", "## Certifications"]
        out += [f"- **{x['name']}** — {x['organization']} ({x['date']})" for x in cv["certifications"]]

    return html.unescape("\n".join(out)) + "\n"
