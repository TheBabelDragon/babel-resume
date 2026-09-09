# content/

This directory is the portfolio.
The renderer must not invent claims that are not in these files
or in the GitHub metadata written beside them.

`.generated/` is written by `python3 scripts/github_sync.py` and is gitignored.

- `github.json` — live evidence for listed and discovered repos
- `discovered.yml` — stubs for public repos not yet curated in `projects.yml`

Curated YAML always overrides a discovered stub with the same `repo:`.
