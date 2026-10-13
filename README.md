# SmartxCV — Streamlit Edition (v3)

A free, local and private AI CV builder with a professional, animated interface.

## Design (v3)

- Clean light theme with a sticky top bar and a ☰ menu (no sidebar)
- **Step-by-step CV Builder**: Personal → Experience → Education → Skills → Projects → Certificates → Finish,
  with a sticky **live A4 preview** that updates as you type
- Home hero with a **3D stack of your real CV pages** (mouse parallax) over an animated perspective dot-wave
- Subtle, eased motion: staggered page entrances, masked headline reveal, card lift on hover, animated score rings
- ⋯ menu on every entry (edit, move up/down, delete)
- **Website CV**: a professional personal site with scroll reveals, a rotating role headline, animated skill bars and
  a 3D-tilt profile card. Download it as `index.html` and host it free (GitHub Pages / Netlify)
- No external JavaScript libraries; all animations respect "reduce motion" settings

## Features

- Edit, reorder and delete entries in every section
- Profile photo upload (used by the Modern template and the digital CV)
- Skills with proficiency levels, plus bulk add (comma-separated)
- ✨ "Polish with AI" for experience and project entries
- CV strength score with an actionable checklist
- Smarter ATS analyzer: phrase detection (e.g. "power bi"), British/American spelling, weighted scoring,
  structure checks, add-missing-skills, and scan history with a chart
- Offline smart engine that rewrites your own facts (summary, bullets, cover letter, tailored CV) when Ollama isn't running
- Tone control and "use as my profile summary" in the AI Writer
- Four distinct print-ready templates (ATS-Friendly, Modern, Professional, Minimal) with a custom accent colour
- One-click Print / Save as PDF; export to HTML, Markdown and JSON
- JSON backup and restore, demo data loader, and a safe "clear all data" action
- Ollama model picker and connection check in Settings

## Installation

**One command (Windows):** double-click `run.bat`, or run:

```powershell
.\run.bat
```

The first run creates the `venv`, installs the requirements, then opens SmartxCV at http://localhost:8501.
Later runs start in seconds. Requires Python 3.10+ (tick "Add python.exe to PATH" when installing).

📘 Full guide: [docs/SmartxCV_User_Manual.pdf](docs/SmartxCV_User_Manual.pdf)

Manual setup, if you prefer:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Tip: on first launch, click **Or explore with a demo CV** on the Home page to see every feature filled in.

## Optional local AI

Install [Ollama](https://ollama.com), then:

```powershell
ollama pull llama3.2
```

Select the model in **Settings → Local AI**. If Ollama is not running, the app uses its offline engine automatically.

## Project structure

```text
├── app.py               # database, AI, ATS logic and all pages
├── cv_templates.py      # printable CV templates + Markdown export
├── ui_effects.py        # theme CSS, 3D hero, score rings, website CV
├── assets/              # SmartxCV logo (full size, 256px, 64px favicon)
├── requirements.txt
├── .streamlit/config.toml
├── data/
│   ├── cvforge.db       # SQLite (migrated automatically from v1)
│   └── photos/
├── backup/app_v1.py     # original version
└── services/fastapi_reference.py
```

Pages: Home · CV Builder · AI Studio (writer, job match, history, tailored CV, cover letter) ·
Design & Download · Website CV · Settings.

## Important

This is a portfolio project. The ATS percentage is a keyword matching indicator, not a real employer ATS score.
The AI must not be used to invent qualifications, experience, achievements or skills.
