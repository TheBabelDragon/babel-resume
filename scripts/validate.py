#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build import load_portfolio

data = load_portfolio()
errors = []

if not data["site"].get("name"):
    errors.append("site.name is required")
if not data["projects"]:
    errors.append("at least one project is required")

ids = set()
for p in data["projects"]:
    if not p.get("id"):
        errors.append("project missing id")
    elif p["id"] in ids:
        errors.append(f"duplicate project id: {p['id']}")
    else:
        ids.add(p["id"])
    if not p.get("name"):
        errors.append(f"project {p.get('id')} missing name")
    if not p.get("repo"):
        errors.append(f"project {p.get('id')} missing repo")
    for key in ("live", "tests_url", "examples_url", "docs_url"):
        url = p.get(key)
        if url and not str(url).startswith("http"):
            errors.append(f"project {p.get('id')} {key} must be an absolute http(s) URL")

nodes = data["systems"].get("nodes") or []
node_ids = {n["id"] for n in nodes}
for n in nodes:
    if n.get("kind") == "project" and n.get("project") and n["project"] not in ids:
        errors.append(f"systems node {n['id']} points at missing project {n['project']}")
    if n.get("kind") != "project" and not n.get("href"):
        errors.append(f"systems abstract node {n['id']} missing href")
for e in data["systems"].get("edges") or []:
    if e["from"] not in node_ids:
        errors.append(f"edge from unknown node: {e['from']}")
    if e["to"] not in node_ids:
        errors.append(f"edge to unknown node: {e['to']}")
for row in data["systems"].get("layout") or []:
    for nid in row:
        if nid not in node_ids:
            errors.append(f"layout references unknown node: {nid}")
for ev in data["timeline"]:
    if ev.get("project") and ev["project"] not in ids:
        errors.append(f"timeline event points at missing project: {ev['project']}")
for item in data["lab"].get("items") or []:
    if item.get("project") and item["project"] not in ids:
        errors.append(f"lab item {item.get('id')} points at missing project {item['project']}")
for sid in data["resume"].get("selected") or []:
    if sid not in ids:
        errors.append(f"resume selected unknown project: {sid}")
for link in data["resume"].get("links") or []:
    if link.get("action"):
        continue
    if not link.get("href"):
        errors.append(f"resume link {link.get('label')} missing href")

if errors:
    print("Portfolio validation failed:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(f"ok  {len(data['projects'])} projects  {len(data['systems'].get('edges') or [])} edges")
