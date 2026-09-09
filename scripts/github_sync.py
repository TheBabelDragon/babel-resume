#!/usr/bin/env python3
"""Refresh GitHub evidence and discover public repos not yet in projects.yml.

Curated YAML in git wins. This script writes generated stubs and, in the
build workspace only, appends them to content/projects.yml and content/lab.yml
so the existing renderer publishes new public repos without a manual edit.
Those workspace writes are not committed (.generated/ is gitignored; the
YAML mutations live only for the current Actions run).
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build import CONTENT, load_yaml  # noqa: E402

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "babel-resume",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def get_json(url: str):
    req = urllib.request.Request(url, headers=headers())
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.load(res), res.headers


def paginate(url: str) -> list:
    out = []
    while url:
        body, hdrs = get_json(url)
        if isinstance(body, list):
            out.extend(body)
        else:
            out.append(body)
        url = None
        link = hdrs.get("Link") or hdrs.get("link") or ""
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<") + 1 : part.find(">")]
    return out


def meta(j: dict) -> dict:
    return {
        "full_name": j.get("full_name"),
        "description": j.get("description"),
        "html_url": j.get("html_url"),
        "language": j.get("language"),
        "stars": j.get("stargazers_count"),
        "forks": j.get("forks_count"),
        "open_issues": j.get("open_issues_count"),
        "pushed_at": j.get("pushed_at"),
        "created_at": j.get("created_at"),
        "default_branch": j.get("default_branch"),
        "topics": j.get("topics") or [],
        "has_pages": bool(j.get("has_pages")),
        "private": bool(j.get("private")),
        "archived": bool(j.get("archived")),
        "fork": bool(j.get("fork")),
    }


def infer_category(name: str, description: str, language: str, topics: list) -> str:
    blob = " ".join([name, description or "", " ".join(topics)]).lower()
    if any(w in blob for w in ("esp32", "firmware", "fpga", "ultrasonic", "laser", "can-fd", "optical", "hardware")):
        return "hardware"
    if any(w in blob for w in ("qcd", "wilson", "lattice", "simulation", "field engine")):
        return "simulation"
    if any(w in blob for w in ("csi", "wifi", "eeg", "sensing")):
        return "sensing"
    if language in {"JavaScript", "TypeScript"} or any(w in blob for w in ("glyph", "visual", "pages", "canvas")):
        return "visual computing"
    if any(w in blob for w in ("pid", "control", "closed-loop")):
        return "control"
    if any(w in blob for w in ("abi", "protocol", "bus")):
        return "protocol"
    if any(w in blob for w in ("agent", "operator", "ai", "llm")):
        return "AI infrastructure"
    if language in {"C", "C++"}:
        return "hardware"
    if language == "Rust":
        return "systems"
    return "systems"


def infer_id(full_name: str, taken: set) -> str:
    name = full_name.split("/", 1)[-1].lower().replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", name).strip("-") or "repo"
    if slug not in taken:
        return slug
    extra = full_name.split("/", 1)[-1].lower()
    alt = re.sub(r"[^a-z0-9-]+", "-", extra).strip("-")
    n = 2
    cand = alt
    while cand in taken:
        cand = f"{alt}-{n}"
        n += 1
    return cand


def title_case(name: str) -> str:
    if name.isupper() or "-" not in name and name.lower() != name:
        return name
    return name.replace("-", " ").replace("_", " ")


def stub_from_repo(j: dict, taken: set) -> dict:
    full = j["full_name"]
    desc = (j.get("description") or "").strip()
    headline = desc.split(".")[0].strip() if desc else full
    if len(headline) > 90:
        headline = headline[:87] + "..."
    pid = infer_id(full, taken)
    taken.add(pid)
    user, repo = full.split("/", 1)
    live = f"https://{user.lower()}.github.io/{repo}/" if j.get("has_pages") else None
    language = j.get("language") or ""
    topics = j.get("topics") or []
    out = {
        "id": pid,
        "name": title_case(repo),
        "status": "experimental",
        "category": infer_category(repo, desc, language, topics),
        "repo": full,
        "headline": headline or repo,
        "description": desc or f"Public repository {full}. Auto-discovered; not yet curated.",
        "technologies": [language] if language else [],
        "demonstrates": topics[:6] or ["public repository"],
        "featured": False,
        "lab": True,
        "discovered": True,
        "status_detail": {
            "stage": "experimental",
            "build": "unknown",
            "tests": "unknown",
            "documentation": "partial" if desc else "unknown",
            "hardware": "none",
        },
    }
    if live:
        out["live"] = live
    return out


def yaml_dump(doc) -> str:
    import yaml

    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


def apply_workspace(projects, discovered):
    if not discovered:
        return
    merged = list(projects) + discovered
    (CONTENT / "projects.yml").write_text(yaml_dump({"projects": merged}))
    lab_doc = load_yaml("lab.yml")
    lab = lab_doc["lab"]
    items = list(lab.get("items") or [])
    seen = {i.get("project") or i.get("id") for i in items}
    for p in discovered:
        if p["id"] in seen:
            continue
        items.append({
            "id": p["id"],
            "name": p.get("name") or p["id"],
            "status": p.get("status") or "experimental",
            "project": p["id"],
            "blurb": p.get("headline") or p.get("description") or "",
        })
        seen.add(p["id"])
    lab["items"] = items
    (CONTENT / "lab.yml").write_text(yaml_dump(lab_doc))
    print(f"workspace merge {len(discovered)} discovered projects")


def main() -> int:
    site = load_yaml("site.yml")["site"]
    discover = site.get("discover") or {}
    enabled = discover.get("enabled", True)
    include_private = bool(discover.get("include_private"))
    ignore = {str(x).lower() for x in (discover.get("ignore_repos") or [])}
    user = site.get("github_user") or "TheBabelDragon"

    projects = load_yaml("projects.yml")["projects"]
    known_repos = {str(p.get("repo") or "").lower() for p in projects if p.get("repo")}
    taken_ids = {p["id"] for p in projects if p.get("id")}

    listed = paginate(f"{API}/users/{urllib.parse.quote(user)}/repos?per_page=100&type=owner&sort=updated")
    catalog = {}
    discovered = []
    for j in listed:
        full = j.get("full_name") or ""
        if not full:
            continue
        if j.get("fork") or j.get("archived"):
            print("skip", full, "fork/archived")
            continue
        if j.get("private") and not include_private:
            print("skip", full, "private")
            continue
        if full.lower() in ignore or full.split("/", 1)[-1].lower() in ignore:
            print("skip", full, "ignored")
            continue
        catalog[full] = meta(j)
        if enabled and full.lower() not in known_repos:
            discovered.append(stub_from_repo(j, taken_ids))
            print("discover", full)
        else:
            print("synced", full)

    for repo in sorted(known_repos):
        if not repo or any(m.get("full_name", "").lower() == repo for m in catalog.values()):
            continue
        try:
            body, _ = get_json(f"{API}/repos/{repo}")
            catalog[body.get("full_name") or repo] = meta(body)
            print("synced", repo)
        except Exception as err:
            print("skip", repo, err)

    dest = CONTENT / ".generated"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "github.json").write_text(json.dumps(catalog, indent=2) + "\n")
    (dest / "discovered.yml").write_text(yaml_dump({"projects": discovered}))
    apply_workspace(projects, discovered)
    print(f"wrote {len(catalog)} github records, {len(discovered)} discovered stubs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
