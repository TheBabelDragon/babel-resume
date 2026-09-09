# babel-resume

YAML → renderer → GitHub Pages.

A GitHub-native engineering portfolio. Repositories are the evidence. YAML is the source of truth.

Not a LinkedIn page. Not a CMS. Not 47 hand-maintained HTML cards.

```
YAML SOURCE OF TRUTH
        |
        v
 GITHUB SYNC + DISCOVERY
        |
        v
 STATIC BUILDER
        |
        v
  GITHUB PAGES
```

This repository is both **the Babel Dragon portfolio** and a **forkable template**.

## Deploy your own

1. Fork this repository.
2. Edit `content/site.yml` (`name`, `github_user`, `base_path`).
3. Edit `content/projects.yml` for curated dossiers.
4. Edit `content/systems.yml` if you want a graph.
5. Settings → Pages → Source: **GitHub Actions**.
6. Push to `main`.

If the repo is `you/babel-resume`, keep `base_path: "/babel-resume"`.
If the repo is `you.github.io`, set `base_path: ""`.

## Auto-populate new projects

`scripts/github_sync.py` does two jobs on every deploy and on the daily cron:

1. Refresh live GitHub evidence (language, last push, stars) for every curated `repo:`.
2. Discover public, non-fork, non-archived repositories under `site.github_user` that are not yet in `content/projects.yml`.

Discovered repos become lab cards automatically. They are **not** written back into `projects.yml`. Curated YAML still wins.

Promote a discovered repo by copying its stub into `content/projects.yml` and writing the real problem / approach / architecture. Ignore a repo:

```yaml
# content/site.yml
site:
  discover:
    enabled: true
    include_private: false
    ignore_repos:
      - some-scratch-repo
```

Private repositories stay off the public site unless you list them yourself.

## Edit the portfolio

| File | What it drives |
| --- | --- |
| `content/site.yml` | Name, nav, tagline, discovery rules |
| `content/projects.yml` | Cards, dossiers, tech index |
| `content/systems.yml` | Homepage map + `/systems` graph |
| `content/resume.yml` | `/resume` (print to PDF) |
| `content/timeline.yml` | `/timeline` |
| `content/lab.yml` | `/lab` experiments |
| `content/principle.yml` | `/principle` — how the stack is built |

## Local

```bash
python3 -m pip install -r requirements.txt
python3 scripts/validate.py
python3 scripts/github_sync.py
python3 src/build.py
```

Live after Pages is enabled: https://thebabeldragon.github.io/babel-resume/
