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
    path = p if p.startswith("/") else "/" + p
    return base_prefix(site) + path

def project_href(site, pid):
    return href(site, "/projects/" + pid + "/")

def node_url(site, n):
    if n.get("kind") == "project" and n.get("project"):
        return project_href(site, n["project"])
    raw = n.get("href") or ""
    return href(site, raw) if raw else ""

def btn(label, url, solid=False, external=False, action=""):
    klass = "btn solid" if solid else "btn"
    if action == "print":
        return '<button class="' + klass + '" type="button" onclick="window.print()">' + esc(label) + '</button>'
    if not url:
        return ""
    rel = ' target="_blank" rel="noopener"' if external or str(url).startswith("http") else ""
    return '<a class="' + klass + '" href="' + esc(url) + '"' + rel + '>' + esc(label) + '</a>'

def status_dot(status):
    s = (status or "unknown").lower()
    return '<span><span class="dot ' + esc(s) + '"></span>' + esc(s) + '</span>'

def mark(v):
    v = str(v)
    if v in {"passing", "yes", "ok"}:
        return "ok"
    if v in {"partial", "prototype", "experimental"}:
        return "partial"
    return "unknown"

def status_strip(d):
    d = d or {}
    bits = []
    for label, key in [("stage", "stage"), ("build", "build"), ("tests", "tests"), ("docs", "documentation"), ("hw", "hardware")]:
        v = d.get(key) or "-"
        bits.append('<span class="' + mark(v) + '">' + esc(label) + ' ' + esc(v) + '</span>')
    return '<div class="status-strip">' + ''.join(bits) + '</div>'

def project_card(site, p):
    url = project_href(site, p["id"])
    return (
        '<a class="card" href="' + esc(url) + '">'
        + '<h3>' + esc(p["name"]) + '</h3>'
        + '<p class="headline">' + esc(p.get("headline") or "") + '</p>'
        + '<div class="meta-row">' + status_dot(p.get("status"))
        + '<span>' + esc(p.get("category") or "") + '</span></div></a>'
    )

def layout(data, title, path, body):
    site, nav, foot = data["site"], data["navigation"], data["footer"]
    items = []
    for item in nav:
        url = item["href"] if item.get("external") else href(site, item["href"])
        cur = ' aria-current="page"' if (not item.get("external") and path == item["href"]) else ""
        rel = ' target="_blank" rel="noopener"' if item.get("external") else ""
        items.append('<li><a href="' + esc(url) + '"' + cur + rel + '>' + esc(item["label"]) + '</a></li>')
    foot_links = (
        '<a href="' + esc(href(site, "/resume/")) + '">resume</a> · '
        + '<a href="' + esc(href(site, "/timeline/")) + '">timeline</a> · '
        + '<a href="' + esc(href(site, "/tech/")) + '">index</a> · '
        + '<a href="' + esc(site.get("github_org_url") or "#") + '">' + esc(site.get("github_user") or "") + '</a>'
    )
    return (
        '<!doctype html><html lang="en"><head>'
        + '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        + '<title>' + esc(title) + '</title>'
        + '<meta name="description" content="' + esc(site.get("description") or "") + '">'
        + '<link rel="preconnect" href="https://fonts.googleapis.com">'
        + '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">'
        + '<link rel="stylesheet" href="' + esc(href(site, "/assets/site.css")) + '"></head><body>'
        + '<header class="site-header"><div class="wrap row">'
        + '<a class="brand" href="' + esc(href(site, "/")) + '">' + esc(site.get("short") or site["name"])
        + '<small>' + esc(site.get("lab_label") or "ENGINEERING / LAB") + '</small></a>'
        + '<nav><ul>' + ''.join(items) + '</ul></nav></div></header>'
        + '<main><div class="wrap">' + body + '</div></main>'
        + '<footer class="site-footer"><div class="wrap row"><div>' + esc(foot.get("line") or "") + '</div>'
        + '<div>' + foot_links + '</div></div></footer>'
        + '</body></html>'
    )

def page(data, path, title, inner):
    return layout(data, title + " — " + data["site"]["name"], path, inner)

def ascii_map(systems):
    rows = systems.get("layout") or []
    label = {n["id"]: n.get("label") or n["id"] for n in systems.get("nodes") or []}
    lines = []
    for i, row in enumerate(rows):
        lines.append("      " + "   ".join("[ " + label.get(x, x) + " ]" for x in row))
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
        parts.append('<path class="edge" d="M %s %s C %s %s, %s %s, %s %s" />' % (x1, y1, x1, mid, x2, mid, x2, y2))
        parts.append('<text class="rel" text-anchor="middle" x="%s" y="%s">%s</text>' % ((x1 + x2) / 2, mid - 4, esc(e.get("relationship") or "")))
    for nid, (x, y) in pos.items():
        n = by_id.get(nid) or {"id": nid, "label": nid}
        url = node_url(site, n)
        klass = "abs" if n.get("kind") == "abstract" else ""
        inner = '<rect class="node-box %s" x="%s" y="%s" width="%s" height="%s" rx="2"/><text text-anchor="middle" x="%s" y="%s">%s</text>' % (klass, x, y, bw, bh, x + bw / 2, y + 22, esc(n.get("label") or nid))
        parts.append(('<a href="' + esc(url) + '">' + inner + '</a>') if url else inner)
    return '<svg class="sys-svg" viewBox="0 0 %s %s" role="img">%s</svg>' % (width, height, ''.join(parts))

def render_home(data):
    cards = "".join(project_card(data["site"], p) for p in data["projects"] if p.get("featured"))
    btns = []
    for item in data["navigation"]:
        url = item["href"] if item.get("external") else href(data["site"], item["href"])
        btns.append(btn(item["label"], url, external=bool(item.get("external"))))
    site = data["site"]
    body = (
        '<section class="hero"><p class="kicker">' + esc(site["title"]) + '</p>'
        + '<h1>' + esc(site["name"]) + '</h1>'
        + '<p class="disciplines">' + esc(site.get("disciplines") or "") + '</p>'
        + '<p class="tagline">' + esc(site.get("tagline") or "") + '</p>'
        + '<div class="cta-row">' + ''.join(btns) + '</div></section>'
        + '<section class="block"><p class="section-label">Currently building</p><div class="grid-2">' + cards + '</div></section>'
        + '<section class="block"><p class="section-label">System map</p>'
        + '<div class="map">' + esc(ascii_map(data["systems"])) + '</div>'
        + '<p class="headline" style="margin-top:14px;color:var(--ink-mute)">Projects are not isolated pieces. '
        + '<a href="' + esc(href(site, "/systems/")) + '">Open the map</a></p></section>'
    )
    return page(data, "/", site["title"], body)

def render_projects(data):
    cards = "".join(project_card(data["site"], p) for p in data["projects"])
    body = (
        '<section class="hero"><p class="kicker">Evidence</p><h1>Projects</h1>'
        + '<p class="tagline">What was actually built. Repositories attached.</p>'
        + '<input class="search" id="q" placeholder="filter" type="search"></section>'
        + '<section class="block"><div class="grid-2" id="grid">' + cards + '</div></section>'
        + "<script>const q=document.getElementById('q'),cs=[...document.querySelectorAll('#grid .card')];"
        + "q.addEventListener('input',()=>{const s=q.value.toLowerCase();cs.forEach(c=>c.style.display=c.textContent.toLowerCase().includes(s)?'':'none')});</script>"
    )
    return page(data, "/projects/", "Projects", body)

def render_project(data, p):
    repo_url = ("https://github.com/" + p["repo"]) if p.get("repo") else ""
    gh = p.get("github") or {}
    gh_line = ""
    if gh:
        gh_line = str(gh.get("language") or "-") + " | " + str(gh.get("pushed_at") or "")[:10] + " | " + str(gh.get("stars", 0))
    proves = "".join("<li>" + esc(x) + "</li>" for x in (p.get("proves") or p.get("demonstrates") or []))
    techs = "".join("<li>" + esc(t) + "</li>" for t in (p.get("technologies") or []))
    approach = ('<p class="rule">The approach</p><div class="preblock">' + esc(p["approach"]) + '</div>') if p.get("approach") else ""
    arch = ('<p class="rule">Architecture</p><div class="preblock">' + esc(p["architecture"]) + '</div>') if p.get("architecture") else ""
    repo_cell = ('<a href="' + esc(repo_url) + '" target="_blank" rel="noopener">' + esc(p["repo"]) + '</a>') if repo_url else "-"
    impl = p.get("implementation") or " / ".join(p.get("technologies") or [])
    actions = (
        btn("View source", repo_url, solid=True, external=True)
        + btn("Open live", p.get("live"), external=True)
        + btn("View tests", p.get("tests_url"), external=True)
        + btn("View examples", p.get("examples_url"), external=True)
        + btn("View docs", p.get("docs_url"), external=True)
        + btn("All projects", href(data["site"], "/projects/"))
    )
    body = (
        '<section class="dossier-head"><p class="kicker">' + esc(p.get("category") or "project") + '</p>'
        + '<h1>' + esc(p["name"]) + '</h1><dl class="kv">'
        + '<dt>Status</dt><dd>' + status_dot(p.get("status")) + '</dd>'
        + '<dt>Repository</dt><dd>' + repo_cell + '</dd>'
        + '<dt>Evidence</dt><dd class="mono">' + esc(gh_line) + '</dd></dl>'
        + '<div style="margin-top:18px">' + status_strip(p.get("status_detail")) + '</div></section>'
        + '<p class="rule">The problem</p><div class="prose"><p>' + esc(p.get("problem") or p.get("description") or "") + '</p></div>'
        + approach + arch
        + (('<p class="rule">What it proves</p><ul class="checks">' + proves + '</ul>') if proves else '')
        + '<p class="rule">Implementation</p><p class="headline">' + esc(impl) + '</p>'
        + (('<ul class="tech-list" style="margin-top:12px">' + techs + '</ul>') if techs else '')
        + '<div class="cta-row" style="margin:28px 0 48px">' + actions + '</div>'
    )
    return page(data, "/projects/" + p["id"] + "/", p["name"], body)

def render_systems(data):
    nodes = {n["id"]: n for n in data["systems"].get("nodes") or []}
    rows = []
    for e in data["systems"].get("edges") or []:
        fr = nodes.get(e["from"], {})
        to = nodes.get(e["to"], {})
        rows.append("<tr><td>" + esc(fr.get("label") or e["from"]) + "</td><td class='mono'>" + esc(e.get("relationship")) + "</td><td>" + esc(to.get("label") or e["to"]) + "</td></tr>")
    body = (
        '<section class="hero"><p class="kicker">Relationships</p><h1>System map</h1>'
        + '<p class="tagline">Not a project list. An engineering ecosystem. Every node is a link.</p></section>'
        + '<section class="block">' + svg_map(data["site"], data["systems"]) + '</section>'
        + '<section class="block"><p class="section-label">Admitted edges</p>'
        + '<table class="stack-table"><thead><tr><th>From</th><th>Rel</th><th>To</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></section>'
    )
    return page(data, "/systems/", "Systems", body)

def render_lab(data):
    cards = []
    for item in data["lab"].get("items") or []:
        inner = "<h3>" + esc(item["name"]) + "</h3><p class='headline'>" + esc(item.get("blurb") or "") + "</p><div class='meta-row'>" + status_dot(item.get("status")) + "<span>lab</span></div>"
        if item.get("project"):
            cards.append('<a class="card" href="' + esc(project_href(data["site"], item["project"])) + '">' + inner + '</a>')
        else:
            cards.append('<div class="card">' + inner + '</div>')
    body = (
        '<section class="hero"><p class="kicker">Experimental</p><h1>Lab</h1>'
        + '<p class="tagline">' + esc(data["lab"].get("intro") or "") + '</p></section>'
        + '<section class="block"><div class="grid-2">' + ''.join(cards) + '</div></section>'
    )
    return page(data, "/lab/", "Lab", body)

def render_resume(data):
    r = data["resume"]
    site = data["site"]
    cap = r.get("capabilities") or {}
    cap_rows = "".join("<tr><th>" + esc(k) + "</th><td>" + " | ".join(esc(v) for v in (vals or [])) + "</td></tr>" for k, vals in cap.items())
    selected = "".join(project_card(site, data["by_id"][i]) for i in r.get("selected") or [] if i in data["by_id"])
    notes = "".join("<li>" + esc(n) + "</li>" for n in r.get("notes") or [])
    links = []
    for item in r.get("links") or []:
        url = "" if item.get("action") else href(site, item.get("href") or "")
        links.append(btn(item.get("label") or "link", url, external=bool(item.get("external")), action=item.get("action") or ""))
    def articles(items):
        out = []
        for job in items or []:
            url = href(site, job["href"]) if job.get("href") else ""
            title = esc(job.get("title") or "")
            if url:
                title = '<a href="' + esc(url) + '">' + title + '</a>'
            out.append(
                '<article class="axiom"><h3>' + esc(job.get("period") or "") + ' — ' + title + '</h3>'
                + '<p class="headline">' + esc(job.get("org") or "") + '</p>'
                + '<div class="prose"><p>' + esc(job.get("body") or "") + '</p></div></article>'
            )
        return "".join(out)
    jobs = articles(r.get("experience"))
    edu = articles(r.get("education"))
    body = (
        '<section class="hero"><p class="kicker">Human-readable index</p>'
        + '<h1>' + esc(r.get("name") or site["name"]) + '</h1>'
        + '<p class="disciplines">' + esc(r.get("role") or "") + '</p>'
        + '<p class="tagline">' + esc(r.get("summary") or "") + '</p>'
        + '<div class="cta-row">' + ''.join(links) + '</div></section>'
        + '<section class="block"><p class="section-label">Record</p>' + jobs + '</section>'
        + (('<section class="block"><p class="section-label">Education</p>' + edu + '</section>') if edu else '')
        + '<section class="block"><p class="section-label">Capabilities</p><table class="stack-table">' + cap_rows + '</table></section>'
        + '<section class="block"><p class="section-label">Selected work</p><div class="grid-2">' + selected + '</div></section>'
        + '<section class="block"><ul class="checks">' + notes + '</ul></section>'
    )
    return page(data, "/resume/", "Resume", body)

def render_timeline(data):
    items = []
    for ev in sorted(data["timeline"], key=lambda e: str(e.get("date") or ""), reverse=True):
        p = data["by_id"].get(ev.get("project"))
        name = p["name"] if p else (ev.get("project") or "")
        link = ('<a href="' + esc(project_href(data["site"], p["id"])) + '">' + esc(name) + '</a>') if p else esc(name)
        items.append('<li><div class="when">' + esc(ev.get("date")) + '</div><div class="rail"></div><div><h3>' + link + '</h3><p>' + esc(ev.get("event")) + '</p></div></li>')
    body = '<section class="hero"><p class="kicker">Record</p><h1>Timeline</h1><p class="tagline">Work dated. Every heading is a dossier.</p></section><section class="block"><ol class="timeline">' + ''.join(items) + '</ol></section>'
    return page(data, "/timeline/", "Timeline", body)

def render_principle(data):
    p = data["principle"]
    axioms = "".join('<article class="axiom"><h3>' + esc(a["title"]) + '</h3><div class="prose"><p>' + esc(a["body"]) + '</p></div></article>' for a in p.get("axioms") or [])
    stack = "".join("<tr><th>" + esc(row["layer"]) + "</th><td>" + " | ".join(esc(i) for i in row.get("items") or []) + "</td></tr>" for row in p.get("stack") or [])
    body = (
        '<section class="hero"><p class="kicker">' + esc(p.get("kicker") or "") + '</p>'
        + '<h1>' + esc(p["title"]) + '</h1><p class="tagline">' + esc(p.get("statement") or "") + '</p></section>'
        + '<section class="block">' + axioms + '</section>'
        + '<section class="block"><p class="section-label">The loop</p><div class="preblock">' + esc(p.get("loop") or "") + '</div></section>'
        + '<section class="block"><p class="section-label">Stack</p><table class="stack-table">' + stack + '</table></section>'
    )
    return page(data, "/principle/", p["title"], body)

def render_tech(data):
    mapping = {}
    for p in data["projects"]:
        for t in p.get("technologies") or []:
            mapping.setdefault(t, []).append(p)
    blocks = []
    for t in sorted(mapping):
        links = " | ".join('<a href="' + esc(project_href(data["site"], p["id"])) + '">' + esc(p["name"]) + '</a>' for p in mapping[t])
        blocks.append("<tr><th>" + esc(t) + "</th><td>" + links + "</td></tr>")
    body = '<section class="hero"><p class="kicker">Derived</p><h1>Technology index</h1><p class="tagline">Generated from project YAML. Every name is a link.</p></section><section class="block"><table class="stack-table">' + ''.join(blocks) + '</table></section>'
    return page(data, "/tech/", "Index", body)

def write_page(url_path, html):
    rel = "index.html" if url_path == "/" else url_path.lstrip("/") + "index.html"
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
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    write_page("/", render_home(data))
    write_page("/projects/", render_projects(data))
    for p in data["projects"]:
        write_page("/projects/" + p["id"] + "/", render_project(data, p))
    write_page("/systems/", render_systems(data))
    write_page("/lab/", render_lab(data))
    write_page("/resume/", render_resume(data))
    write_page("/timeline/", render_timeline(data))
    write_page("/principle/", render_principle(data))
    write_page("/tech/", render_tech(data))
    payload = {"site": data["site"], "projects": [{"id": p["id"], "name": p["name"], "status": p.get("status"), "repo": p.get("repo"), "headline": p.get("headline")} for p in data["projects"]], "generated_at": datetime.now(timezone.utc).isoformat()}
    (DIST / "portfolio.json").write_text(json.dumps(payload, indent=2))
    (DIST / ".nojekyll").write_text("")
    print("built", len(data["projects"]), "project pages -> dist/")

if __name__ == "__main__":
    build()
