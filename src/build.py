#!/usr/bin/env python3
"""YAML -> static GitHub Pages site."""
from __future__ import annotations
import json, shutil
from datetime import datetime, timezone
from html import escape as esc
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT, DIST = ROOT / "content", ROOT / "dist"

def load_yaml(name):
    return yaml.safe_load((CONTENT / name).read_text())

def load_portfolio():
    site_doc = load_yaml("site.yml")
    projects = load_yaml("projects.yml")["projects"]
    github = {}
    gen = CONTENT / ".generated" / "github.json"
    if gen.exists():
        github = json.loads(gen.read_text())
    for p in projects:
        p["github"] = github.get(p.get("repo") or "") or None
    return {
        "site": site_doc["site"],
        "navigation": site_doc.get("navigation") or [],
        "footer": site_doc.get("footer") or {},
        "projects": projects,
        "by_id": {p["id"]: p for p in projects},
        "systems": load_yaml("systems.yml"),
        "resume": load_yaml("resume.yml")["resume"],
        "timeline": load_yaml("timeline.yml")["timeline"] or [],
        "lab": load_yaml("lab.yml")["lab"],
        "principle": load_yaml("principle.yml")["principle"],
        "github": github,
    }

def base_prefix(site):
    raw = site.get("base_path") or ""
    if not raw or raw == "/":
        return ""
    return raw[:-1] if raw.endswith("/") else raw

def href(site, p):
    if not p:
        return base_prefix(site) + "/"
    if str(p).startswith("http"):
        return p
    return f"{base_prefix(site)}{p if p.startswith('/') else '/' + p}"

def status_dot(status):
    s = (status or "unknown").lower()
    return f'<span><span class="dot {esc(s)}"></span>{esc(s)}</span>'

def mark(v):
    v = str(v)
    if v in {"passing", "yes", "ok"}: return "ok"
    if v in {"partial", "prototype", "experimental"}: return "partial"
    return "unknown"

def status_strip(d):
    d = d or {}
    def cell(label, key):
        v = d.get(key) or "-"
        return f'<span class="{mark(v)}">{esc(label)} {esc(v)}</span>'
    return '<div class="status-strip">' + cell("stage","stage") + cell("build","build") + cell("tests","tests") + cell("docs","documentation") + cell("hw","hardware") + "</div>"

def project_card(site, p):
    return f"""<a class="card" href="{esc(href(site, f'/projects/{p[\"id\"]}/'))}">
    <h3>{esc(p['name'])}</h3>
    <p class="headline">{esc(p.get('headline') or '')}</p>
    <div class="meta-row">{status_dot(p.get('status'))}<span>{esc(p.get('category') or '')}</span></div></a>"""

def layout(data, title, path, body):
    site, nav, foot = data["site"], data["navigation"], data["footer"]
    items = []
    for item in nav:
        url = item["href"] if item.get("external") else href(site, item["href"])
        cur = ' aria-current="page"' if (not item.get("external") and path == item["href"]) else ""
        rel = ' target="_blank" rel="noopener"' if item.get("external") else ""
        items.append(f'<li><a href="{esc(url)}"{cur}{rel}>{esc(item["label"])}</a></li>')
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(site.get('description') or '')}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<link rel="stylesheet" href="{esc(href(site, '/assets/site.css'))}"></head><body>
<header class="site-header"><div class="wrap row">
<a class="brand" href="{esc(href(site, '/'))}">{esc(site.get('short') or site['name'])}<small>{esc(site.get('lab_label') or 'ENGINEERING / LAB')}</small></a>
<nav><ul>{''.join(items)}</ul></nav></div></header>
<main><div class="wrap">{body}</div></main>
<footer class="site-footer"><div class="wrap row"><div>{esc(foot.get('line') or '')}</div>
<div><a href="{esc(site.get('github_org_url') or '#')}">{esc(site.get('github_user') or '')}</a></div></div></footer>
</body></html>"""

def page(data, path, title, inner):
    return layout(data, f"{title} — {data['site']['name']}", path, inner)

def ascii_map(systems):
    rows = systems.get("layout") or []
    label = {n["id"]: n.get("label") or n["id"] for n in systems.get("nodes") or []}
    lines = []
    for i, row in enumerate(rows):
        lines.append("      " + "   ".join(f"[ {label.get(x, x)} ]" for x in row))
        if i < len(rows) - 1:
            n = max(len(row), len(rows[i + 1]))
            lines.append("      " + "  ".join(["    |    "] * n).rstrip())
    return "\n".join(lines)

def svg_map(site, systems):
    rows = systems.get("layout") or []
    by_id = {n["id"]: n for n in systems.get("nodes") or []}
    bw, bh, gx, gy, pad = 150, 36, 28, 70, 20
    cols = max((len(r) for r in rows), default=1)
    width = pad * 2 + cols * bw + (cols - 1) * gx
    height = pad * 2 + len(rows) * bh + max(0, len(rows) - 1) * gy
    pos = {}
    for r, row in enumerate(rows):
        rw = len(row) * bw + max(0, len(row) - 1) * gx
        sx = (width - rw) / 2
        for c, nid in enumerate(row):
            pos[nid] = (sx + c * (bw + gx), pad + r * (bh + gy))
    parts = []
    for e in systems.get("edges") or []:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        ax, ay = pos[e["from"]]; bx, by_ = pos[e["to"]]
        x1, y1, x2, y2 = ax + bw / 2, ay + bh, bx + bw / 2, by_
        mid = (y1 + y2) / 2
        parts.append(f'<path class="edge" d="M {x1} {y1} C {x1} {mid}, {x2} {mid}, {x2} {y2}" />')
        parts.append(f'<text class="rel" text-anchor="middle" x="{(x1+x2)/2}" y="{mid-4}">{esc(e.get("relationship") or "")}</text>')
    for nid, (x, y) in pos.items():
        n = by_id.get(nid) or {"id": nid, "label": nid}
        url = href(site, f"/projects/{n['project']}/") if n.get("kind") == "project" and n.get("project") else (n.get("href") or "")
        klass = "abs" if n.get("kind") == "abstract" else ""
        inner = f'<rect class="node-box {klass}" x="{x}" y="{y}" width="{bw}" height="{bh}" rx="2"/><text text-anchor="middle" x="{x+bw/2}" y="{y+22}">{esc(n.get("label") or nid)}</text>'
        parts.append(f'<a href="{esc(url)}">{inner}</a>' if url else inner)
    return f'<svg class="sys-svg" viewBox="0 0 {width} {height}" role="img">{''.join(parts)}</svg>'

def render_home(data):
    cards = "".join(project_card(data["site"], p) for p in data["projects"] if p.get("featured"))
    btns = []
    for item in data["navigation"]:
        url = item["href"] if item.get("external") else href(data["site"], item["href"])
        rel = ' target="_blank" rel="noopener"' if item.get("external") else ""
        btns.append(f'<a class="btn" href="{esc(url)}"{rel}>{esc(item["label"])}</a>')
    return page(data, "/", data["site"]["title"], f"""<section class="hero">
<p class="kicker">{esc(data['site']['title'])}</p><h1>{esc(data['site']['name'])}</h1>
<p class="disciplines">{esc(data['site'].get('disciplines') or '')}</p>
<p class="tagline">{esc(data['site'].get('tagline') or '')}</p>
<div class="cta-row">{''.join(btns)}</div></section>
<section class="block"><p class="section-label">Currently building</p><div class="grid-2">{cards}</div></section>
<section class="block"><p class="section-label">System map</p>
<div class="map">{esc(ascii_map(data['systems']))}</div>
<p class="headline" style="margin-top:14px;color:var(--ink-mute)">Projects are not isolated pieces.
<a href="{esc(href(data['site'], '/systems/'))}">Open the map</a></p></section>""")

def render_projects(data):
    cards = "".join(project_card(data["site"], p) for p in data["projects"])
    return page(data, "/projects/", "Projects", f"""<section class="hero"><p class="kicker">Evidence</p><h1>Projects</h1>
<p class="tagline">What was actually built. Repositories attached.</p>
<input class="search" id="q" placeholder="filter…" type="search"></section>
<section class="block"><div class="grid-2" id="grid">{cards}</div></section>
<script>const q=document.getElementById('q'),cs=[...document.querySelectorAll('#grid .card')];
q.addEventListener('input',()=>{{const s=q.value.toLowerCase();cs.forEach(c=>c.style.display=c.textContent.toLowerCase().includes(s)?'':'none')}});</script>""")

def render_project(data, p):
    repo_url = f"https://github.com/{p['repo']}" if p.get("repo") else ""
    gh = p.get("github") or {}
    gh_line = f"{gh.get('language') or '-'} · {str(gh.get('pushed_at') or '')[:10]} · {gh.get('stars', 0)}*" if gh else ""
    proves = "".join(f"<li>{esc(x)}</li>" for x in (p.get("proves") or p.get("demonstrates") or []))
    techs = "".join(f"<li>{esc(t)}</li>" for t in (p.get("technologies") or []))
    approach = f'<p class="rule">The approach</p><div class="preblock">{esc(p["approach"])}</div>' if p.get("approach") else ""
    arch = f'<p class="rule">Architecture</p><div class="preblock">{esc(p["architecture"])}</div>' if p.get("architecture") else ""
    repo_cell = f'<a href="{esc(repo_url)}" target="_blank" rel="noopener">{esc(p["repo"])}</a>' if repo_url else "-"
    src = f'<a class="btn solid" href="{esc(repo_url)}" target="_blank" rel="noopener">View source</a>' if repo_url else ""
    impl = p.get("implementation") or " / ".join(p.get("technologies") or [])
    return page(data, f"/projects/{p['id']}/", p["name"], f"""<section class="dossier-head">
<p class="kicker">{esc(p.get('category') or 'project')}</p><h1>{esc(p['name'])}</h1>
<dl class="kv"><dt>Status</dt><dd>{status_dot(p.get('status'))}</dd>
<dt>Repository</dt><dd>{repo_cell}</dd><dt>Evidence</dt><dd class="mono">{esc(gh_line)}</dd></dl>
<div style="margin-top:18px">{status_strip(p.get('status_detail'))}</div></section>
<p class="rule">The problem</p><div class="prose"><p>{esc(p.get('problem') or p.get('description') or '')}</p></div>
{approach}{arch}
{('<p class="rule">What it proves</p><ul class="checks">'+proves+'</ul>') if proves else ''}
<p class="rule">Implementation</p><p class="headline">{esc(impl)}</p>
{('<ul class="tech-list" style="margin-top:12px">'+techs+'</ul>') if techs else ''}
<div class="cta-row" style="margin:28px 0 48px">{src}<a class="btn" href="{esc(href(data['site'], '/projects/'))}">All projects</a></div>""")

def render_systems(data):
    nodes = {n["id"]: n for n in data["systems"].get("nodes") or []}
    rows = "".join(
        f"<tr><td>{esc(nodes.get(e['from'],{}).get('label') or e['from'])}</td><td class='mono'>{esc(e.get('relationship'))}</td><td>{esc(nodes.get(e['to'],{}).get('label') or e['to'])}</td></tr>"
        for e in data["systems"].get("edges") or [])
    return page(data, "/systems/", "Systems", f"""<section class="hero"><p class="kicker">Relationships</p><h1>System map</h1>
<p class="tagline">Not a project list. An engineering ecosystem.</p></section>
<section class="block">{svg_map(data['site'], data['systems'])}</section>
<section class="block"><p class="section-label">Admitted edges</p>
<table class="stack-table"><thead><tr><th>From</th><th>Rel</th><th>To</th></tr></thead><tbody>{rows}</tbody></table></section>""")

def render_lab(data):
    cards = []
    for item in data["lab"].get("items") or []:
        inner = f"<h3>{esc(item['name'])}</h3><p class='headline'>{esc(item.get('blurb') or '')}</p><div class='meta-row'>{status_dot(item.get('status'))}<span>lab</span></div>"
        if item.get("project"):
            cards.append(f'<a class="card" href="{esc(href(data["site"], f"/projects/{item[\"project\"]}/"))}">{inner}</a>')
        else:
            cards.append(f'<div class="card">{inner}</div>')
    return page(data, "/lab/", "Lab", f"""<section class="hero"><p class="kicker">Experimental</p><h1>Lab</h1>
<p class="tagline">{esc(data['lab'].get('intro') or '')}</p></section>
<section class="block"><div class="grid-2">{''.join(cards)}</div></section>""")

def render_resume(data):
    cap = data["resume"].get("capabilities") or {}
    cap_rows = "".join(f"<tr><th>{esc(k)}</th><td>{' · '.join(esc(v) for v in (vals or []))}</td></tr>" for k, vals in cap.items())
    selected = "".join(project_card(data["site"], data["by_id"][i]) for i in data["resume"].get("selected") or [] if i in data["by_id"])
    notes = "".join(f"<li>{esc(n)}</li>" for n in data["resume"].get("notes") or [])
    return page(data, "/resume/", "Resume", f"""<section class="hero"><p class="kicker">Human-readable index</p>
<h1>{esc(data['resume'].get('name') or data['site']['name'])}</h1>
<p class="disciplines">{esc(data['resume'].get('role') or '')}</p>
<p class="tagline">{esc(data['resume'].get('summary') or '')}</p>
<div class="cta-row"><a class="btn" href="{esc(data['site'].get('github_org_url') or '#')}" target="_blank" rel="noopener">GitHub</a>
<button class="btn" onclick="window.print()">Print / PDF</button></div></section>
<section class="block"><p class="section-label">Capabilities</p><table class="stack-table">{cap_rows}</table></section>
<section class="block"><p class="section-label">Selected work</p><div class="grid-2">{selected}</div></section>
<section class="block"><ul class="checks">{notes}</ul></section>""")

def render_timeline(data):
    items = []
    for ev in sorted(data["timeline"], key=lambda e: str(e.get("date") or ""), reverse=True):
        p = data["by_id"].get(ev.get("project"))
        name = p["name"] if p else (ev.get("project") or "")
        link = f'<a href="{esc(href(data["site"], f"/projects/{p[\"id\"]}/"))}">{esc(name)}</a>' if p else esc(name)
        items.append(f'<li><div class="when">{esc(ev.get("date"))}</div><div class="rail"></div><div><h3>{link}</h3><p>{esc(ev.get("event"))}</p></div></li>')
    return page(data, "/timeline/", "Timeline", f"""<section class="hero"><p class="kicker">Record</p><h1>Timeline</h1>
<p class="tagline">Work dated.</p></section><section class="block"><ol class="timeline">{''.join(items)}</ol></section>""")

def render_principle(data):
    p = data["principle"]
    axioms = "".join(f'<article class="axiom"><h3>{esc(a["title"])}</h3><div class="prose"><p>{esc(a["body"])}</p></div></article>' for a in p.get("axioms") or [])
    stack = "".join(f"<tr><th>{esc(row['layer'])}</th><td>{' · '.join(esc(i) for i in row.get('items') or [])}</td></tr>" for row in p.get("stack") or [])
    return page(data, "/principle/", p["title"], f"""<section class="hero"><p class="kicker">{esc(p.get('kicker') or '')}</p>
<h1>{esc(p['title'])}</h1><p class="tagline">{esc(p.get('statement') or '')}</p></section>
<section class="block">{axioms}</section>
<section class="block"><p class="section-label">The loop</p><div class="preblock">{esc(p.get('loop') or '')}</div></section>
<section class="block"><p class="section-label">Stack</p><table class="stack-table">{stack}</table></section>""")

def render_tech(data):
    mapping = {}
    for p in data["projects"]:
        for t in p.get("technologies") or []:
            mapping.setdefault(t, []).append(p)
    blocks = []
    for t in sorted(mapping):
        links = " · ".join(f'<a href="{esc(href(data["site"], f"/projects/{p[\"id\"]}/"))}">{esc(p["name"])}</a>' for p in mapping[t])
        blocks.append(f"<tr><th>{esc(t)}</th><td>{links}</td></tr>")
    return page(data, "/tech/", "Index", f"""<section class="hero"><p class="kicker">Derived</p><h1>Technology index</h1>
<p class="tagline">Generated from project YAML.</p></section>
<section class="block"><table class="stack-table">{''.join(blocks)}</table></section>""")

def write_page(url_path, html):
    rel = "index.html" if url_path == "/" else f"{url_path.lstrip('/')}index.html"
    dest = DIST / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html)

def build():
    data = load_portfolio()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST / "assets").mkdir()
    shutil.copy2(ROOT / "src" / "css" / "site.css", DIST / "assets" / "site.css")
    public = ROOT / "public"
    if public.exists():
        for item in public.iterdir():
            dest = DIST / item.name
            if item.is_dir(): shutil.copytree(item, dest, dirs_exist_ok=True)
            else: shutil.copy2(item, dest)
    write_page("/", render_home(data))
    write_page("/projects/", render_projects(data))
    for p in data["projects"]:
        write_page(f"/projects/{p['id']}/", render_project(data, p))
    write_page("/systems/", render_systems(data))
    write_page("/lab/", render_lab(data))
    write_page("/resume/", render_resume(data))
    write_page("/timeline/", render_timeline(data))
    write_page("/principle/", render_principle(data))
    write_page("/tech/", render_tech(data))
    payload = {"site": data["site"], "projects": [{"id": p["id"], "name": p["name"], "status": p.get("status"), "repo": p.get("repo"), "headline": p.get("headline")} for p in data["projects"]], "generated_at": datetime.now(timezone.utc).isoformat()}
    (DIST / "portfolio.json").write_text(json.dumps(payload, indent=2))
    (DIST / ".nojekyll").write_text("")
    print(f"built {len(data['projects'])} project pages -> dist/")

if __name__ == "__main__":
    build()
