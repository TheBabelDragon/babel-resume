"""Merge auto-discovered GitHub repos into the curated portfolio."""
from __future__ import annotations

import json
from pathlib import Path

import yaml


def attach_github(projects, github):
    by_full = github
    by_lower = {str(k).lower(): v for k, v in github.items()}
    for p in projects:
        repo = p.get("repo") or ""
        p["github"] = by_full.get(repo) or by_lower.get(repo.lower()) or None


def merge_discovered(content_dir: Path, projects):
    path = content_dir / ".generated" / "discovered.yml"
    if not path.exists():
        return projects
    doc = yaml.safe_load(path.read_text()) or {}
    extra = doc.get("projects") or []
    if not extra:
        return projects
    known_repos = {str(p.get("repo") or "").lower() for p in projects}
    known_ids = {p["id"] for p in projects if p.get("id")}
    out = list(projects)
    for p in extra:
        repo = str(p.get("repo") or "").lower()
        if repo and repo in known_repos:
            continue
        if p.get("id") in known_ids:
            p["id"] = str(p["id"]) + "-discovered"
        out.append(p)
        known_ids.add(p["id"])
        if repo:
            known_repos.add(repo)
    return out


def merge_lab(lab, projects):
    items = list(lab.get("items") or [])
    seen = {i.get("project") or i.get("id") for i in items}
    for p in projects:
        if not p.get("discovered"):
            continue
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
    lab = dict(lab)
    lab["items"] = items
    return lab


def sort_projects(projects):
    curated = [p for p in projects if not p.get("discovered")]
    discovered = [p for p in projects if p.get("discovered")]
    curated_featured = [p for p in curated if p.get("featured")]
    curated_rest = [p for p in curated if not p.get("featured")]
    curated_rest.sort(key=lambda p: str((p.get("github") or {}).get("pushed_at") or ""), reverse=True)
    discovered.sort(key=lambda p: str((p.get("github") or {}).get("pushed_at") or ""), reverse=True)
    return curated_featured + curated_rest + discovered


def load_github(content_dir: Path):
    gen = content_dir / ".generated" / "github.json"
    if not gen.exists():
        return {}
    return json.loads(gen.read_text())
