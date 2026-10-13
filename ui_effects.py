"""
SmartxCV - visual layer (v3, professional light theme).

- global_css(accent): theme for the Streamlit app (no sidebar, sticky top bar)
- hero_3d(...): 3D stack of the user's real CV pages over an animated dot-wave
- gauge(...): animated score ring
- digital_cv(...): standalone personal website

All motion uses ease-out curves, respects prefers-reduced-motion, and needs
no external JavaScript libraries (works offline).
"""

from __future__ import annotations

import html
import json

FONTS_LINK = (
    "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap'>"
)

EASE = "cubic-bezier(.16,1,.3,1)"


def to_js(data):
    """JSON that is safe to inline inside a <script> tag."""
    return json.dumps(data).replace("</", "<\\/")


def esc(value):
    return html.escape(str(value or ""))


# ============================================================
# SHARED JS: perspective dot-wave (canvas 2D, no dependencies)
# ============================================================

DOT_WAVE_JS = """
function dotWave(canvas, color, o) {
  o = Object.assign({ cols: 90, rows: 28, gap: 26, amp: 16, speed: .55, alpha: .5, horizon: .42, track: window }, o || {});
  const ctx = canvas.getContext('2d');
  const m = /^#?([\\da-f]{2})([\\da-f]{2})([\\da-f]{2})$/i.exec(color) || [0, '25', '63', 'eb'];
  const rgb = [1, 2, 3].map(i => parseInt(m[i], 16)).join(',');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let w = 0, h = 0, mx = 0, tmx = 0;
  function size() {
    const d = Math.min(devicePixelRatio || 1, 2); w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * d; canvas.height = h * d; ctx.setTransform(d, 0, 0, d, 0, 0);
  }
  size(); addEventListener('resize', size);
  o.track.addEventListener('mousemove', e => { tmx = e.clientX / innerWidth - .5; });
  function frame(ms) {
    const t = ms * .001 * o.speed; mx += (tmx - mx) * .04;
    ctx.clearRect(0, 0, w, h);
    const f = 300, cy = h * o.horizon, cx = w / 2 + mx * 80;
    for (let r = 0; r < o.rows; r++) {
      const s = f / (200 + r * o.gap), a = o.alpha * Math.pow(1 - r / o.rows, 1.4);
      ctx.fillStyle = `rgba(${rgb},${a})`;
      for (let c = 0; c < o.cols; c++) {
        const x = (c - o.cols / 2) * o.gap;
        const y = Math.sin(c * .2 + t * 1.3) * o.amp + Math.cos(r * .33 + t) * o.amp * .8;
        const sx = cx + x * s, sy = cy + (y + 140) * s;
        if (sx < -4 || sx > w + 4 || sy < -4 || sy > h + 4) continue;
        const rad = Math.min(2.4, 1.5 * s);
        ctx.fillRect(sx - rad / 2, sy - rad / 2, rad, rad);
      }
    }
    if (!reduce) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
"""


# ============================================================
# GLOBAL STREAMLIT THEME
# ============================================================

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
:root{
  --brand:__ACCENT__;--brand-soft:color-mix(in srgb,__ACCENT__ 10%,#fff);--brand-ring:color-mix(in srgb,__ACCENT__ 22%,transparent);
  --gold:#e9a23b;--gold-deep:#c97a16;--gold-soft:#fdf3e1;
  --bg:#faf7f1;--surface:#fff;--line:#ebe5d9;--line-2:#ddd4c4;--ink:#10241f;--ink-2:#34433f;--muted:#6b7570;
  --ok:#15803d;--ok-soft:#ecf8ef;--bad:#c2410c;--bad-soft:#fff1ea;--warn:#c97a16;
  --shadow-sm:0 1px 2px rgba(16,36,31,.05),0 1px 3px rgba(16,36,31,.06);
  --shadow-md:0 4px 6px -2px rgba(16,36,31,.05),0 14px 28px -8px rgba(16,36,31,.12);
  --shadow-lg:0 26px 52px -18px rgba(16,36,31,.26);
  --ease:cubic-bezier(.16,1,.3,1);
}
html,body,.stApp{font-family:'Inter',system-ui,sans-serif;color:var(--ink)}
.stApp{background:var(--bg)}
h1,h2,h3,h4{font-family:'Plus Jakarta Sans','Inter',sans-serif!important;color:var(--ink);letter-spacing:-.02em}

/* chrome: no streamlit header, no sidebar */
[data-testid="stHeader"],[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],
[data-testid="stToolbar"],[data-testid="stDecoration"],footer{display:none!important}
.block-container{padding:0 1.25rem 4rem!important;max-width:1260px}

/* entrance motion: staggered rise on mount */
@keyframes cf-rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes cf-fade{from{opacity:0}to{opacity:1}}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]>div{animation:cf-rise .7s var(--ease) both}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]>div:nth-child(2){animation-delay:.04s}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]>div:nth-child(3){animation-delay:.08s}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]>div:nth-child(4){animation-delay:.12s}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]>div:nth-child(5){animation-delay:.16s}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]>div:nth-child(n+6){animation-delay:.2s}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* top bar */
.st-key-topbar{position:sticky;top:0;z-index:1000;margin:0 -1.25rem 1.6rem;padding:.65rem 1.25rem;
  background:rgba(250,247,241,.82);backdrop-filter:saturate(180%) blur(14px);-webkit-backdrop-filter:saturate(180%) blur(14px);
  border-bottom:1px solid var(--line);animation:cf-fade .5s ease both!important}
.cf-brand{display:flex;align-items:center;gap:10px;font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:1.15rem;color:var(--ink);white-space:nowrap}
.cf-brand i{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;font-style:normal;color:#fff;font-size:15px;
  background:linear-gradient(135deg,var(--brand),color-mix(in srgb,var(--brand) 55%,#0ea5e9));box-shadow:0 6px 14px -6px var(--brand)}
.cf-brand span{color:var(--muted);font-weight:600}
.cf-meter{display:flex;align-items:center;gap:10px;font-size:.82rem;color:var(--muted);white-space:nowrap}
.cf-meter .track{width:120px;height:6px;border-radius:99px;background:var(--line);overflow:hidden}
.cf-meter .track i{display:block;height:100%;border-radius:inherit;background:var(--brand);transition:width .9s var(--ease)}
.cf-meter b{color:var(--ink)}
[data-testid="stPopoverBody"]{border-radius:14px!important;border:1px solid var(--line)!important;box-shadow:var(--shadow-lg)!important;
  padding:.5rem!important;min-width:250px;animation:cf-rise .35s var(--ease) both}
[data-testid="stPopoverBody"] [data-testid="stPageLink"] a{border-radius:10px;padding:.45rem .7rem;transition:background .15s}
[data-testid="stPopoverBody"] [data-testid="stPageLink"] a:hover{background:var(--brand-soft)}
.cf-menu-label{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:.4rem .7rem .1rem}

/* inputs */
[data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],[data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] .react-aria-ComboBox [role="group"],[data-testid="stMultiSelect"] [role="group"],
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{
  background:#fbfcfe!important;border:none!important;border-radius:10px!important;
  box-shadow:inset 0 0 0 1px var(--line-2)!important;transition:box-shadow .2s,background .2s}
[data-testid="stTextInputRootElement"] input,[data-testid="stTextAreaRootElement"] textarea{background:transparent!important}
[data-testid="stTextInputRootElement"]:hover,[data-testid="stTextAreaRootElement"]:hover,
[data-testid="stSelectbox"] .react-aria-ComboBox [role="group"]:hover{box-shadow:inset 0 0 0 1px #b4bfd1!important}
[data-testid="stTextInputRootElement"]:focus-within,[data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stSelectbox"] .react-aria-ComboBox [role="group"]:focus-within,
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{
  background:#fff!important;box-shadow:inset 0 0 0 1.5px var(--brand),0 0 0 4px var(--brand-ring)!important}
[data-testid="stWidgetLabel"] p{font-weight:600;color:var(--ink-2);font-size:.86rem}

/* surfaces */
[data-testid="stForm"]{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:1.4rem 1.4rem .9rem;box-shadow:var(--shadow-sm)}
[data-testid="stExpander"] details{background:var(--surface);border:1px solid var(--line)!important;border-radius:14px;box-shadow:var(--shadow-sm)}
[class*="st-key-card"]{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:1.1rem 1.2rem;
  box-shadow:var(--shadow-sm);transition:box-shadow .35s var(--ease),transform .35s var(--ease),border-color .35s}
[class*="st-key-card"]:hover{box-shadow:var(--shadow-md);transform:translateY(-2px);border-color:var(--line-2)}
[data-testid="stMetric"]{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:1rem 1.2rem;box-shadow:var(--shadow-sm)}
[data-testid="stMetricValue"]{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800}
iframe{border-radius:14px}
[data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid var(--line)}
[data-baseweb="tab"]{padding:.6rem 1rem!important;font-weight:600}

/* buttons */
.stButton button,.stDownloadButton button,[data-testid="stFormSubmitButton"] button,[data-testid="stPopover"]>div>button{
  border-radius:10px;font-weight:600;transition:transform .15s var(--ease),box-shadow .25s,background .2s,border-color .2s,color .2s}
.stButton button:active,.stDownloadButton button:active,[data-testid="stFormSubmitButton"] button:active{transform:scale(.97)}
button[data-testid^="stBaseButton-primary"]{background:var(--brand)!important;border:1px solid var(--brand)!important;color:#fff!important;
  box-shadow:0 1px 2px rgba(15,23,42,.1),0 6px 16px -8px var(--brand)}
button[data-testid^="stBaseButton-primary"]:hover{filter:brightness(1.07);box-shadow:0 10px 22px -10px var(--brand)}
button[data-testid^="stBaseButton-secondary"]{background:var(--surface)!important;border:1px solid var(--line-2)!important}
button[data-testid^="stBaseButton-secondary"]:hover{border-color:var(--brand)!important;color:var(--brand)!important}
.st-key-cta [data-testid="stPageLink"] a{background:var(--brand);color:#fff;border-radius:12px;padding:.75rem 1.2rem;
  box-shadow:0 10px 24px -10px var(--brand);transition:transform .25s var(--ease),box-shadow .25s}
.st-key-cta [data-testid="stPageLink"] a p{color:#fff!important;font-weight:700}
.st-key-cta [data-testid="stPageLink"] a:hover{transform:translateY(-2px);box-shadow:0 16px 30px -12px var(--brand)}
.st-key-cta2 [data-testid="stPageLink"] a{background:var(--surface);border:1px solid var(--line-2);border-radius:12px;padding:.75rem 1.2rem;transition:border-color .2s,transform .25s var(--ease)}
.st-key-cta2 [data-testid="stPageLink"] a:hover{border-color:var(--brand);transform:translateY(-2px)}
.st-key-cta2 [data-testid="stPageLink"] a p{font-weight:700}

/* stepper */
.st-key-stepper button{border:none!important;background:transparent!important;box-shadow:none!important;color:var(--muted)!important;padding:.35rem .6rem!important}
.st-key-stepper button:hover{color:var(--ink)!important;background:var(--surface)!important}
.st-key-stepper button[data-testid^="stBaseButton-primary"]{background:var(--brand-soft)!important;color:var(--brand)!important}
.cf-steps-line{height:3px;border-radius:99px;background:var(--line);margin:.2rem 0 1.4rem;overflow:hidden}
.cf-steps-line i{display:block;height:100%;background:var(--brand);border-radius:inherit;transition:width .8s var(--ease)}

/* sticky live preview */
[data-testid="stHorizontalBlock"]:has(.st-key-preview){align-items:flex-start}
.st-key-preview{position:sticky;top:84px}
.st-key-preview iframe{box-shadow:var(--shadow-lg);animation:cf-fade .6s ease both}

/* small components */
.cf-head{margin:.3rem 0 1.4rem}
.cf-eyebrow{font-size:.74rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand)}
.cf-head h1{font-size:2rem;font-weight:800;margin:.3rem 0 0;padding:0;line-height:1.15}
.cf-head p{color:var(--muted);margin:.4rem 0 0;font-size:1rem;max-width:720px}
.cf-chip{display:inline-block;padding:3px 10px;margin:3px 5px 3px 0;border-radius:999px;font-size:.8rem;font-weight:500;
  border:1px solid var(--line);background:var(--surface);color:var(--ink-2)}
.cf-chip.ok{border-color:#a7f3d0;background:var(--ok-soft);color:#047857}
.cf-chip.miss{border-color:#fecaca;background:var(--bad-soft);color:#b91c1c}
.cf-entry h4{margin:0;font-size:1rem;font-weight:700}
.cf-entry .sub{color:var(--muted);font-size:.84rem;margin-top:2px}
.cf-entry .body{color:var(--ink-2);font-size:.86rem;margin-top:8px;white-space:pre-line;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.cf-check{display:flex;gap:12px;align-items:flex-start;padding:.6rem 0;border-bottom:1px solid var(--line)}
.cf-check:last-child{border-bottom:none}
.cf-check .ic{flex:none;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700}
.cf-check .ic.ok{background:var(--ok-soft);color:var(--ok)}
.cf-check .ic.no{background:#fff7ed;color:var(--warn)}
.cf-check b{font-weight:600;font-size:.9rem}
.cf-check .tip{display:block;color:var(--muted);font-size:.8rem}
.cf-tool h4{margin:.5rem 0 .2rem;font-size:1rem}
.cf-tool p{margin:0;color:var(--muted);font-size:.86rem}
.cf-tool .ico{width:40px;height:40px;border-radius:11px;display:grid;place-items:center;font-size:19px;background:var(--brand-soft)}
.cf-hero .h1{font-family:'Plus Jakarta Sans',sans-serif;color:var(--ink);font-size:clamp(2.2rem,4vw,3.2rem);line-height:1.08;font-weight:800;margin:.6rem 0 1rem!important;padding:0!important;letter-spacing:-.035em}
.cf-hero h1 a,.cf-head h1 a{display:none!important}
.cf-head h1{padding:0!important}
.cf-hero .h1 em{font-style:normal;color:var(--brand)}
.cf-hero p{font-size:1.08rem;color:var(--ink-2);max-width:520px;line-height:1.65}
.cf-hero .line{display:block;overflow:hidden}
.cf-hero .line>span{display:inline-block;animation:cf-up 1s var(--ease) both}
@keyframes cf-up{from{transform:translateY(105%)}to{transform:none}}
.cf-trust{display:flex;flex-wrap:wrap;gap:18px;margin-top:1.4rem;color:var(--muted);font-size:.85rem}
.cf-trust span::before{content:"✓";color:var(--ok);font-weight:700;margin-right:6px}
.cf-skill{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:.9rem;font-weight:600}
.cf-dots{display:inline-flex;gap:3px}
.cf-dots i{width:7px;height:7px;border-radius:50%;background:var(--line-2)}
.cf-dots i.on{background:var(--brand)}

/* ---- SmartxCV brand & classic motion ---- */
.cf-brand img{width:38px;height:38px;border-radius:10px;object-fit:cover;box-shadow:0 6px 14px -8px rgba(16,36,31,.6);
  transition:transform .6s var(--ease)}
.cf-brand:hover img{transform:rotate(-6deg) scale(1.06)}
.cf-brand b{color:var(--gold-deep);font-weight:800}
.cf-eyebrow{color:var(--gold-deep)!important;display:inline-flex;align-items:center;gap:8px}
.cf-eyebrow::before{content:"";width:18px;height:2px;border-radius:2px;background:var(--gold);
  transform-origin:left;animation:cf-draw .9s var(--ease) .15s both}
@keyframes cf-draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.cf-hero .h1 em{position:relative;white-space:nowrap;isolation:isolate}
.cf-hero .h1 em::after{content:"";position:absolute;left:0;right:0;bottom:.02em;height:.12em;border-radius:99px;
  background:linear-gradient(90deg,var(--gold),color-mix(in srgb,var(--gold) 40%,transparent));
  transform-origin:left;animation:cf-draw 1.1s var(--ease) .9s both;z-index:-1}
/* gentle sheen across primary buttons on hover */
button[data-testid^="stBaseButton-primary"]{position:relative;overflow:hidden}
button[data-testid^="stBaseButton-primary"]::after{content:"";position:absolute;top:0;bottom:0;left:-60%;width:40%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.28),transparent);transform:skewX(-18deg);transition:left .7s var(--ease)}
button[data-testid^="stBaseButton-primary"]:hover::after{left:130%}
/* underline grow on text links */
[data-testid="stPageLink"] a p{background:linear-gradient(var(--gold),var(--gold)) no-repeat 0 100%/0 1.5px;transition:background-size .4s var(--ease)}
[data-testid="stPageLink"] a:hover p{background-size:100% 1.5px}
.st-key-cta [data-testid="stPageLink"] a p,.st-key-cta2 [data-testid="stPageLink"] a p{background:none}
.cf-tool .ico{background:var(--gold-soft);transition:transform .5s var(--ease)}
[class*="st-key-card"]:hover .cf-tool .ico{transform:translateY(-3px) rotate(-4deg)}
.cf-chip.ok{border-color:#bfe3c9!important;color:#166534!important}
.cf-check .ic.no{background:var(--gold-soft)!important;color:var(--gold-deep)!important}
/* first-visit splash */
[data-testid="stVerticalBlock"]>div:has(.cf-splash){animation:none!important}
.cf-splash{position:fixed;inset:0;z-index:100000;display:grid;place-items:center;background:var(--bg);
  animation:cf-splash-out .6s var(--ease) 1.5s forwards}
.cf-splash .in{display:flex;flex-direction:column;align-items:center;gap:18px}
.cf-splash img{width:120px;height:120px;border-radius:28px;box-shadow:var(--shadow-lg);animation:cf-logo 1s var(--ease) both}
.cf-splash .name{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:1.9rem;color:var(--ink);letter-spacing:-.02em;
  animation:cf-name .9s var(--ease) .35s both}
.cf-splash .name b{color:var(--gold-deep)}
.cf-splash .bar{width:140px;height:3px;border-radius:99px;background:var(--line);overflow:hidden}
.cf-splash .bar i{display:block;height:100%;background:linear-gradient(90deg,var(--brand),var(--gold));animation:cf-load 1.3s var(--ease) .2s both}
@keyframes cf-logo{from{opacity:0;transform:scale(.86) translateY(10px)}to{opacity:1;transform:none}}
@keyframes cf-name{from{opacity:0;letter-spacing:.2em}to{opacity:1;letter-spacing:-.02em}}
@keyframes cf-load{from{width:0}to{width:100%}}
@keyframes cf-splash-out{to{opacity:0;visibility:hidden}}
</style>
"""


def global_css(accent):
    return GLOBAL_CSS.replace("__ACCENT__", accent)


def brand_html(logo_uri=""):
    img = f"<img src='{logo_uri}' alt='SmartxCV logo'>" if logo_uri else "<i>S</i>"
    return f"<div class='cf-brand'>{img}<span style='color:var(--ink)'>Smartx<b>CV</b></span></div>"


def splash_html(logo_uri):
    return (f"<div class='cf-splash' aria-hidden='true'><div class='in'><img src='{logo_uri}' alt=''>"
            "<div class='name'>Smartx<b>CV</b></div><div class='bar'><i></i></div></div></div>")


def meter_html(score):
    return (f"<div class='cf-meter'>CV strength <span class='track'><i style='width:{score}%'></i></span>"
            f"<b>{score}%</b></div>")


def header_html(eyebrow, title, subtitle=""):
    return (f"<div class='cf-head'><div class='cf-eyebrow'>{esc(eyebrow)}</div><h1>{esc(title)}</h1>"
            + (f"<p>{esc(subtitle)}</p>" if subtitle else "") + "</div>")


def chips_html(items, kind=""):
    return "".join(f"<span class='cf-chip {kind}'>{esc(x)}</span>" for x in items)


def entry_html(title, subtitle, body):
    return (f"<div class='cf-entry'><h4>{esc(title)}</h4>"
            + (f"<div class='sub'>{esc(subtitle)}</div>" if subtitle else "")
            + (f"<div class='body'>{esc(body)}</div>" if body else "") + "</div>")


def checklist_html(checks):
    return "".join(
        f"<div class='cf-check'><span class='ic {'ok' if c['ok'] else 'no'}'>{'✓' if c['ok'] else '!'}</span>"
        f"<span><b>{esc(c['label'])}</b>" + ("" if c["ok"] else f"<span class='tip'>{esc(c['tip'])}</span>")
        + "</span></div>"
        for c in checks
    )


def steps_line_html(index, total):
    return f"<div class='cf-steps-line'><i style='width:{(index + 1) / total * 100:.1f}%'></i></div>"


def tool_html(icon, title, text):
    return f"<div class='cf-tool'><div class='ico'>{icon}</div><h4>{esc(title)}</h4><p>{esc(text)}</p></div>"


def dots_html(level):
    return "<span class='cf-dots'>" + "".join(
        f"<i class='{'on' if n < level else ''}'></i>" for n in range(5)) + "</span>"


def hero_text_html(eyebrow, line1, line2, text):
    return (
        "<div class='cf-hero'>"
        f"<div class='cf-eyebrow'>{esc(eyebrow)}</div>"
        f"<div class='h1' role='heading' aria-level='1'><span class='line'><span>{esc(line1)}</span></span>"
        f"<span class='line'><span style='animation-delay:.08s'><em>{esc(line2)}</em></span></span></div>"
        f"<p>{esc(text)}</p></div>"
    )


# ============================================================
# HOME HERO: 3D stack of the user's real CV pages
# ============================================================

HERO_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<style>
html,body{margin:0;height:100%;overflow:hidden;background:transparent;font-family:Inter,system-ui,sans-serif}
#stage{position:relative;height:100%;overflow:hidden}
#wave{position:absolute;left:0;right:0;bottom:0;height:62%;width:100%;
  -webkit-mask-image:linear-gradient(transparent,#000 35%);mask-image:linear-gradient(transparent,#000 35%)}
.scene{position:absolute;inset:0;display:grid;place-items:center}
.stack{position:relative;width:__W__px;height:__H__px;transform-style:preserve-3d;
  transform:rotateX(var(--rx,10deg)) rotateY(var(--ry,-22deg)) rotateZ(2deg);transition:transform 1.2s __EASE__}
.sheet{position:absolute;inset:0;border-radius:6px;overflow:hidden;background:#fff;
  box-shadow:0 1px 0 rgba(15,23,42,.04),0 30px 60px -24px rgba(16,36,31,.35),0 12px 24px -12px rgba(16,36,31,.18);
  animation:in 1.4s __EASE__ both}
.sheet iframe{width:794px;height:1123px;border:0;transform:scale(__S__);transform-origin:0 0;pointer-events:none}
.s1{transform:translate3d(0,0,0)}
.s2{transform:translate3d(46px,-26px,-90px);animation-delay:.12s;filter:brightness(.98)}
.s3{transform:translate3d(92px,-52px,-180px);animation-delay:.24s;filter:brightness(.96)}
.s1{animation-delay:.36s}
@keyframes in{from{opacity:0;translate:0 60px}to{opacity:1;translate:0 0}}
.float{perspective:1800px;animation:float 7s ease-in-out infinite}
@keyframes float{50%{translate:0 -10px}}
.chip{position:absolute;display:flex;align-items:center;gap:8px;padding:9px 13px;border-radius:12px;background:rgba(255,255,255,.92);
  backdrop-filter:blur(10px);border:1px solid #e5e9f0;font-size:12.5px;font-weight:600;color:#0f172a;white-space:nowrap;
  box-shadow:0 18px 36px -14px rgba(15,23,42,.3);animation:pop 1s __EASE__ both}
.chip b{font-family:'Plus Jakarta Sans',Inter,sans-serif}
.chip .d{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:13px;color:#fff}
.c1{left:-70px;top:18%;transform:translateZ(90px);animation-delay:.9s}
.c2{right:-80px;top:44%;transform:translateZ(130px);animation-delay:1.05s}
.c3{left:-40px;bottom:12%;transform:translateZ(110px);animation-delay:1.2s}
@keyframes pop{from{opacity:0;scale:.85;translate:0 12px}to{opacity:1;scale:1;translate:0 0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>__FONTS__</head><body>
<div id="stage"><canvas id="wave"></canvas>
<div class="scene"><div class="float"><div class="stack" id="stack">
  <div class="sheet s3"><iframe srcdoc="__CV3__" tabindex="-1"></iframe></div>
  <div class="sheet s2"><iframe srcdoc="__CV2__" tabindex="-1"></iframe></div>
  <div class="sheet s1"><iframe srcdoc="__CV1__" tabindex="-1"></iframe></div>
  <div class="chip c1"><span class="d" style="background:#15803d">✓</span>ATS-friendly layout</div>
  <div class="chip c2"><span class="d" style="background:__ACCENT__">%</span>CV strength&nbsp;<b>__SCORE__%</b></div>
  <div class="chip c3"><span class="d" style="background:#e9a23b">★</span>__TEMPLATE__ template</div>
</div></div></div></div>
<script>
__DOTWAVE__
dotWave(document.getElementById('wave'), '__ACCENT__', { alpha: .45, horizon: .05, amp: 14 });
const stack = document.getElementById('stack');
document.addEventListener('mousemove', e => {
  const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5;
  stack.style.setProperty('--ry', (-22 + x * 16) + 'deg'); stack.style.setProperty('--rx', (10 - y * 10) + 'deg');
});
document.addEventListener('mouseleave', () => { stack.style.removeProperty('--ry'); stack.style.removeProperty('--rx'); });
</script></body></html>"""


def hero_3d(cv_pages, accent, score, template, scale=0.4):
    """cv_pages: three full CV HTML documents (front first)."""
    pages = (list(cv_pages) + list(cv_pages)[:1] * 3)[:3]
    out = (HERO_TEMPLATE.replace("__FONTS__", FONTS_LINK).replace("__DOTWAVE__", DOT_WAVE_JS)
           .replace("__EASE__", EASE).replace("__S__", str(scale))
           .replace("__W__", str(round(794 * scale))).replace("__H__", str(round(1123 * scale)))
           .replace("__ACCENT__", accent).replace("__SCORE__", str(score)).replace("__TEMPLATE__", esc(template)))
    for i, page in enumerate(pages, 1):
        out = out.replace(f"__CV{i}__", html.escape(page, quote=True))
    return out


# ============================================================
# ANIMATED SCORE RING
# ============================================================

GAUGE_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">__FONTS__
<style>
html,body{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif;overflow:hidden}
.w{display:flex;justify-content:center;align-items:center;height:__H__px}
.g{position:relative;width:__S__px;height:__S__px}
svg{width:100%;height:100%;transform:rotate(-90deg)}
.v{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.v b{font-family:'Plus Jakarta Sans',Inter,sans-serif;font-size:__F__px;font-weight:800;color:#0f172a;letter-spacing:-.03em;line-height:1}
.v small{color:#64748b;font-size:11.5px;margin-top:6px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
</style></head><body>
<div class="w"><div class="g">
<svg viewBox="0 0 200 200">
<circle cx="100" cy="100" r="86" fill="none" stroke="#e8edf5" stroke-width="12"/>
<circle id="arc" cx="100" cy="100" r="86" fill="none" stroke="__COLOR__" stroke-width="12" stroke-linecap="round"
  stroke-dasharray="540.35" stroke-dashoffset="540.35"/>
</svg>
<div class="v"><b><span id="n">0</span>%</b><small>__LABEL__</small></div>
</div></div>
<script>
const target = __SCORE__, arc = document.getElementById('arc'), n = document.getElementById('n'), C = 540.35, t0 = performance.now();
const ease = k => 1 - Math.pow(1 - k, 4);
(function f(t) { const k = Math.min((t - t0) / 1600, 1), v = target * ease(k);
  arc.style.strokeDashoffset = C * (1 - v / 100); n.textContent = Math.round(v); if (k < 1) requestAnimationFrame(f); })(t0);
</script></body></html>"""


def score_color(score):
    return "#059669" if score >= 70 else "#d97706" if score >= 45 else "#dc2626"


def gauge(score, label, size=170, color=None):
    score = max(0, min(100, float(score or 0)))
    return (GAUGE_TEMPLATE.replace("__FONTS__", FONTS_LINK)
            .replace("__H__", str(size + 16)).replace("__S__", str(size))
            .replace("__F__", str(int(size * 0.24)))
            .replace("__COLOR__", color or score_color(score)).replace("__LABEL__", esc(label))
            .replace("__SCORE__", str(round(score, 1))))


# ============================================================
# DIGITAL CV (standalone personal website)
# ============================================================

DIGITAL_TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>__FONTS__
<style>
:root{--a:__ACCENT__;--a-soft:color-mix(in srgb,var(--a) 9%,#fff);--bg:#f8fafc;--card:#fff;--line:#e6eaf1;--ink:#0f172a;--ink2:#334155;--mu:#64748b;
  --ease:cubic-bezier(.16,1,.3,1);--sh:0 1px 2px rgba(15,23,42,.05),0 10px 30px -12px rgba(15,23,42,.14)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
h1,h2,h3{font-family:'Plus Jakarta Sans',Inter,sans-serif;letter-spacing:-.025em;margin:0}
nav{position:sticky;top:0;z-index:20;background:rgba(248,250,252,.8);backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid transparent;transition:border-color .3s}
nav.scrolled{border-color:var(--line)}
nav .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
.logo{font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;display:flex;gap:10px;align-items:center}
.logo i{width:30px;height:30px;border-radius:8px;background:var(--a);color:#fff;display:grid;place-items:center;font-style:normal;font-size:13px}
.links{display:flex;gap:26px;font-size:14px;font-weight:500;color:var(--ink2)}
.links a{position:relative}
.links a::after{content:"";position:absolute;left:0;right:0;bottom:-4px;height:2px;background:var(--a);transform:scaleX(0);transform-origin:left;transition:transform .35s var(--ease)}
.links a:hover::after{transform:scaleX(1)}
.btn{display:inline-flex;align-items:center;gap:8px;padding:11px 18px;border-radius:11px;font-size:14px;font-weight:600;border:1px solid var(--line);
  background:var(--card);transition:transform .25s var(--ease),box-shadow .25s,border-color .2s}
.btn:hover{transform:translateY(-2px);box-shadow:var(--sh);border-color:#cfd6e2}
.btn.p{background:var(--a);border-color:var(--a);color:#fff;box-shadow:0 10px 22px -10px var(--a)}
.hero{position:relative;overflow:hidden;padding:72px 0 96px}
#wave{position:absolute;left:0;right:0;bottom:0;width:100%;height:55%;pointer-events:none;
  -webkit-mask-image:linear-gradient(transparent,#000 40%);mask-image:linear-gradient(transparent,#000 40%)}
.hero .wrap{position:relative;display:grid;grid-template-columns:1.2fr .8fr;gap:56px;align-items:center}
.badge{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--ink2);padding:6px 12px;border-radius:99px;background:var(--card);border:1px solid var(--line)}
.badge i{width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 0 4px #d1fae5}
.hero h1{font-size:clamp(40px,6vw,64px);line-height:1.04;margin:18px 0 14px;font-weight:800}
.rot{display:inline-grid;height:1.5em;line-height:1.5em;overflow:hidden;vertical-align:bottom;color:var(--a);font-weight:700}
.rot span{grid-area:1/1;transition:transform .7s var(--ease),opacity .7s var(--ease);transform:translateY(100%);opacity:0}
.rot span.on{transform:none;opacity:1}.rot span.out{transform:translateY(-100%);opacity:0}
.role{font-size:22px;color:var(--ink2);font-family:'Plus Jakarta Sans',sans-serif;font-weight:600}
.lead{color:var(--mu);font-size:17px;max-width:540px;margin:16px 0 28px}
.cta{display:flex;flex-wrap:wrap;gap:10px}
.card-wrap{perspective:1200px}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:28px;box-shadow:0 30px 60px -28px rgba(15,23,42,.3);
  transform-style:preserve-3d;transition:transform .6s var(--ease)}
.avatar{width:96px;height:96px;border-radius:24px;object-fit:cover;display:grid;place-items:center;font-size:34px;font-weight:800;color:#fff;
  font-family:'Plus Jakarta Sans',sans-serif;background:linear-gradient(135deg,var(--a),color-mix(in srgb,var(--a) 50%,#0ea5e9));transform:translateZ(40px)}
.pcard h3{margin-top:18px;font-size:22px;transform:translateZ(30px)}
.pcard .meta{color:var(--mu);font-size:14px;transform:translateZ(20px)}
.kv{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:20px;transform:translateZ(20px)}
.kv div{padding:12px 14px;border-radius:14px;background:var(--bg);border:1px solid var(--line)}
.kv b{display:block;font-family:'Plus Jakarta Sans',sans-serif;font-size:24px;line-height:1.1}
.kv span{font-size:12px;color:var(--mu);font-weight:500}
section{padding:72px 0;border-top:1px solid var(--line)}
.sh{display:grid;grid-template-columns:220px 1fr;gap:40px}
.sh .lbl{font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--a);padding-top:6px}
.sh h2{font-size:30px;margin-bottom:24px}
.about{font-size:19px;color:var(--ink2);line-height:1.7;max-width:720px}
.job{display:grid;grid-template-columns:150px 1fr;gap:24px;padding:22px 0;border-bottom:1px solid var(--line)}
.job:last-child{border-bottom:none}
.when{color:var(--mu);font-size:14px;font-weight:500}
.job h3{font-size:18px}.job .co{color:var(--a);font-weight:600;font-size:15px}
.job ul{margin:10px 0 0;padding-left:18px;color:var(--ink2)}
.ach{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.ach span{font-size:13px;padding:5px 11px;border-radius:99px;background:var(--a-soft);color:var(--ink2);border:1px solid color-mix(in srgb,var(--a) 18%,#fff)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}
.box{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;transition:transform .45s var(--ease),box-shadow .45s var(--ease)}
.box:hover{transform:translateY(-4px);box-shadow:var(--sh)}
.box h3{font-size:17px}
.sk{margin:12px 0}.sk .r{display:flex;justify-content:space-between;font-size:14px;font-weight:500}.sk em{font-style:normal;color:var(--mu);font-size:12px}
.bar{height:6px;border-radius:99px;background:#eef2f7;overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;width:0;border-radius:inherit;background:var(--a);transition:width 1.4s var(--ease)}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}
.tags span{font-size:12px;padding:4px 10px;border-radius:8px;background:var(--bg);border:1px solid var(--line);color:var(--ink2)}
.box p{color:var(--ink2);margin:8px 0 0;font-size:15px}
.box ul{color:var(--ink2);padding-left:18px;margin:8px 0 0;font-size:15px}
.pl{display:flex;gap:16px;margin-top:14px;font-size:14px;font-weight:600;color:var(--a)}
.contact{margin:24px 0 72px;border-radius:24px;padding:48px;background:var(--ink);color:#fff;display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap;position:relative;overflow:hidden}
.contact h2{font-size:32px;color:#fff}.contact p{color:#94a3b8;margin:8px 0 0}
.contact .btn{background:#fff;color:var(--ink);border-color:#fff}
footer{text-align:center;color:var(--mu);font-size:13px;padding:0 0 40px}
.rv{opacity:0;transform:translateY(24px);transition:opacity .9s var(--ease),transform .9s var(--ease);transition-delay:var(--d,0s)}
.rv.in{opacity:1;transform:none}
@media(max-width:860px){.hero .wrap,.sh,.job{grid-template-columns:1fr;gap:20px}.links{display:none}.hero{padding:40px 0 70px}section{padding:52px 0}.contact{padding:32px}}
@media (prefers-reduced-motion:reduce){.rv{opacity:1;transform:none}*{transition:none!important}}
</style></head>
<body><div id="app"></div>
<script>
__DOTWAVE__
const D = __DATA__;
const e = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const lines = t => String(t || '').split(/\\n+/).map(l => l.replace(/^[\\s•\\-*–·]+/, '').trim()).filter(Boolean);
const href = u => /^https?:\\/\\//i.test(u) ? u : 'https://' + u;
const range = (a, b) => [a, b].filter(Boolean).join(' – ');
const list = t => { const l = lines(t); return l.length > 1 ? '<ul>' + l.map(x => `<li>${e(x)}</li>`).join('') + '</ul>' : l.length ? `<p>${e(l[0])}</p>` : ''; };
const P = D.profile;
const initials = (P.full_name || 'CV').split(/\\s+/).filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase();
const avatar = D.photo ? `<img class="avatar" src="${D.photo}" alt="">` : `<div class="avatar">${e(initials)}</div>`;
const sec = (id, lbl, title, body) => body ? `<section id="${id}"><div class="wrap sh"><div class="lbl rv">${lbl}</div><div><h2 class="rv">${title}</h2>${body}</div></div></section>` : '';
const levels = ['', 'Beginner', 'Elementary', 'Intermediate', 'Advanced', 'Expert'];

const groups = {}; D.skills.forEach(s => (groups[s.category || 'Other'] ||= []).push(s));
const skills = Object.keys(groups).length ? `<div class="grid">${Object.entries(groups).map(([c, items], i) => `
  <div class="box rv" style="--d:${i * .06}s"><h3>${e(c)}</h3>${items.map(s => `<div class="sk"><div class="r"><span>${e(s.skill_name)}</span><em>${levels[s.level || 3]}</em></div>
  <div class="bar"><i data-w="${(s.level || 3) * 20}"></i></div></div>`).join('')}</div>`).join('')}</div>` : '';
const exp = D.experience.map((x, i) => `<div class="job rv" style="--d:${i * .05}s"><div class="when">${e(range(x.start_date, x.end_date))}</div><div>
  <h3>${e(x.position)}</h3><div class="co">${e([x.company, x.location].filter(Boolean).join(' · '))}</div>${list(x.responsibilities)}
  ${lines(x.achievements).length ? `<div class="ach">${lines(x.achievements).map(a => `<span>${e(a)}</span>`).join('')}</div>` : ''}</div></div>`).join('');
const proj = D.projects.length ? `<div class="grid">${D.projects.map((x, i) => `<div class="box rv" style="--d:${i * .06}s"><h3>${e(x.name)}</h3>${list(x.description)}
  ${x.technologies ? `<div class="tags">${x.technologies.split(/[,;|]/).map(t => t.trim()).filter(Boolean).map(t => `<span>${e(t)}</span>`).join('')}</div>` : ''}
  <div class="pl">${x.github_url ? `<a target="_blank" rel="noopener" href="${e(href(x.github_url))}">Code ↗</a>` : ''}${x.demo_url ? `<a target="_blank" rel="noopener" href="${e(href(x.demo_url))}">Live ↗</a>` : ''}</div></div>`).join('')}</div>` : '';
const edu = [...D.education.map(x => ({ t: x.degree, s: [x.institution, x.grade].filter(Boolean).join(' · '), w: range(x.start_year, x.end_year), d: x.description })),
             ...D.certifications.map(x => ({ t: x.name, s: x.organization, w: x.date, d: '', u: x.credential_url }))];
const eduHtml = edu.map((x, i) => `<div class="job rv" style="--d:${i * .05}s"><div class="when">${e(x.w)}</div><div><h3>${e(x.t)}</h3><div class="co">${e(x.s)}</div>${list(x.d)}
  ${x.u ? `<div class="pl"><a target="_blank" rel="noopener" href="${e(href(x.u))}">Verify ↗</a></div>` : ''}</div></div>`).join('');

const contactBtns = [
  P.email && `<a class="btn p" href="mailto:${e(P.email)}">Get in touch</a>`,
  P.linkedin && `<a class="btn" target="_blank" rel="noopener" href="${e(href(P.linkedin))}">LinkedIn</a>`,
  P.github && `<a class="btn" target="_blank" rel="noopener" href="${e(href(P.github))}">GitHub</a>`,
  P.portfolio && `<a class="btn" target="_blank" rel="noopener" href="${e(href(P.portfolio))}">Portfolio</a>`,
].filter(Boolean).join('');
const words = [P.title || 'Professional', ...D.skills.slice().sort((a, b) => (b.level || 0) - (a.level || 0)).slice(0, 3).map(s => s.skill_name)];

document.getElementById('app').innerHTML = `
<nav id="nav"><div class="wrap"><div class="logo"><i>${e(initials)}</i>${e(P.full_name || 'Your Name')}</div>
  <div class="links">${P.summary ? '<a href="#about">About</a>' : ''}${D.experience.length ? '<a href="#experience">Experience</a>' : ''}${D.skills.length ? '<a href="#skills">Skills</a>' : ''}${D.projects.length ? '<a href="#projects">Projects</a>' : ''}<a href="#contact">Contact</a></div></div></nav>
<header class="hero"><canvas id="wave"></canvas><div class="wrap">
  <div><span class="badge rv"><i></i>Available for new opportunities</span>
    <h1 class="rv" style="--d:.05s">${e(P.full_name || 'Your Name')}</h1>
    <div class="role rv" style="--d:.1s"><span class="rot">${words.map((w, i) => `<span class="${i ? '' : 'on'}">${e(w)}</span>`).join('')}</span></div>
    ${P.summary ? `<p class="lead rv" style="--d:.15s">${e(P.summary.split(/(?<=[.!?])\\s/)[0])}</p>` : '<div style="height:24px"></div>'}
    <div class="cta rv" style="--d:.2s">${contactBtns}</div></div>
  <div class="card-wrap rv" style="--d:.15s"><div class="pcard" id="pcard">${avatar}<h3>${e(P.full_name || 'Your Name')}</h3>
    <div class="meta">${e([P.title, P.location].filter(Boolean).join(' · '))}</div>
    <div class="kv">${[[D.experience.length, 'Roles'], [D.projects.length, 'Projects'], [D.skills.length, 'Skills'], [D.certifications.length, 'Certificates']]
      .map(([v, l]) => `<div><b data-count="${v}">0</b><span>${l}</span></div>`).join('')}</div></div></div>
</div></header>
${sec('about', 'About', 'A little about me', P.summary ? `<p class="about rv">${e(P.summary)}</p>` : '')}
${sec('experience', 'Experience', 'Where I have worked', exp)}
${sec('skills', 'Skills', 'What I work with', skills)}
${sec('projects', 'Projects', 'Selected work', proj)}
${sec('education', 'Education', 'Education & certificates', eduHtml)}
<div class="wrap"><div class="contact rv" id="contact"><div><h2>Let's work together</h2>
  <p>${e([P.email, P.phone, P.location].filter(Boolean).join(' · '))}</p></div><div class="cta">${contactBtns}</div></div></div>
<footer>© ${new Date().getFullYear()} ${e(P.full_name)} · Built with SmartxCV</footer>`;

dotWave(document.getElementById('wave'), D.accent, { alpha: .4, horizon: .02, amp: 14 });

// rotating role words
const rot = [...document.querySelectorAll('.rot span')]; let ri = 0;
if (rot.length > 1) setInterval(() => { rot[ri].className = 'out'; const prev = rot[ri]; ri = (ri + 1) % rot.length; rot[ri].className = 'on';
  setTimeout(() => { if (prev.className === 'out') prev.className = ''; }, 700); }, 2600);

// subtle 3D tilt
const card = document.getElementById('pcard');
card.addEventListener('mousemove', ev => { const r = card.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width - .5, y = (ev.clientY - r.top) / r.height - .5;
  card.style.transition = 'transform .15s ease-out'; card.style.transform = `rotateY(${x * 10}deg) rotateX(${-y * 10}deg)`; });
card.addEventListener('mouseleave', () => { card.style.transition = ''; card.style.transform = ''; });

// nav border on scroll
const nav = document.getElementById('nav'); addEventListener('scroll', () => nav.classList.toggle('scrolled', scrollY > 10));

// reveal + counters + bars
const count = el => { const to = +el.dataset.count, t0 = performance.now();
  (function f(t) { const k = Math.min((t - t0) / 1400, 1); el.textContent = Math.round(to * (1 - Math.pow(1 - k, 4))); if (k < 1) requestAnimationFrame(f); })(t0); };
const io = new IntersectionObserver(es => es.forEach(en => { if (!en.isIntersecting) return; const t = en.target; t.classList.add('in');
  t.querySelectorAll('.bar i').forEach(b => b.style.width = b.dataset.w + '%'); t.querySelectorAll('[data-count]').forEach(count); io.unobserve(t); }), { threshold: .15 });
document.querySelectorAll('.rv').forEach(el => io.observe(el));
</script></body></html>"""


def digital_cv(data):
    """data: profile, photo (data URI or ''), accent, and the five entry lists."""
    title = esc(data["profile"].get("full_name") or "Digital CV")
    return (DIGITAL_TEMPLATE.replace("__FONTS__", FONTS_LINK).replace("__DOTWAVE__", DOT_WAVE_JS)
            .replace("__TITLE__", title).replace("__ACCENT__", data["accent"])
            .replace("__DATA__", to_js(data)))
