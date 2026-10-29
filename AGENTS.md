# AGENTS.md

This repository builds a static marketing website for zensys.in from YAML and Markdown content. Most work should be content-first, not code-heavy.

## Project shape

- `build.py` is the site generator. It reads `content/`, renders templates from `templates/`, and writes output to `_site/`.
- `content/site.yml` contains shared company data used across the site: phone, email, address, navigation, redirects, and form settings.
- `content/home.yml`, `content/clients.yml`, `content/services/*.md`, `content/pages/*.md`, and `content/blog/*.md` are the source-of-truth content files for the site.
- `templates/` contains the Jinja HTML layouts. Most layout changes are made there rather than in Python logic.
- `static/` contains CSS, JS, fonts, and images; generated assets should not be hand-edited.

## Build and preview

Use these commands for local validation:

```bash
python3 -m pip install -r requirements.txt
python3 build.py
python3 build.py --serve
```

`python3 build.py --serve` starts a local preview at http://localhost:8000.

## Editing conventions

- Prefer updating the relevant YAML/Markdown source file over changing generation logic in `build.py` for day-to-day edits.
- Keep SEO metadata consistent when changing content: `title`, `meta_title`, `description`, `url`, and `h1` should match the page purpose.
- New blog posts should follow the existing pattern in `content/blog/*.md` and end with a `## Frequently Asked Questions` section using `####` question headings.
- Service and page content should stay aligned with the existing front matter pattern used in `content/services/*.md` and `content/pages/*.md`.
- Do not edit generated files in `_site/`; they are build artifacts.
- For redirect or URL changes, update the relevant entries in `content/site.yml` and keep old URLs intentional.

## Useful references

- [README.md](README.md) documents the site purpose, launch notes, and content-editing workflow.
- [build.py](build.py) is the canonical build logic and explains how the site is assembled.

## Working style for agents

- Keep changes narrowly scoped and content-aware.
- When adding or editing pages, reuse the existing schema and template patterns instead of inventing new structures.
- Preserve accessibility, SEO metadata, and the company’s brand tone used across the site.
- Validate with the local build before finalizing changes.
