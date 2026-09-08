#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build import ROOT, load_portfolio

data = load_portfolio()
token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
repos = sorted({p.get("repo") for p in data["projects"] if p.get("repo")})


def fetch_repo(full: str) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{full}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "babel-resume",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        j = json.load(res)
    return {
        "full_name": j.get("full_name"),
        "description": j.get("description"),
        "html_url": j.get("html_url"),
        "language": j.get("language"),
        "stars": j.get("stargazers_count"),
        "forks": j.get("forks_count"),
        "open_issues": j.get("open_issues_count"),
        "pushed_at": j.get("pushed_at"),
        "default_branch": j.get("default_branch"),
        "topics": j.get("topics") or [],
    }


out = {}
for repo in repos:
    try:
        out[repo] = fetch_repo(repo)
        print("synced", repo)
    except Exception as err:
        print("skip", repo, err)

dest = ROOT / "content" / ".generated"
dest.mkdir(parents=True, exist_ok=True)
(dest / "github.json").write_text(json.dumps(out, indent=2))
print(f"wrote {len(out)}/{len(repos)} repos")
