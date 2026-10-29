# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Static marketing site for zensys.in (Bigin by Zoho CRM, payroll software, bulk SMS). A single Python script renders Markdown/YAML content through Jinja2 templates into `_site/`, which GitHub Actions deploys to GitHub Pages on every push to `main` (`.github/workflows/deploy.yml`, Python 3.12). SEO (Google) and AEO (AI answer engines) are primary goals, so structured data, URLs and meta fields matter as much as the visible HTML.

## Commands

```
pip install -r requirements.txt     # markdown, Jinja2, PyYAML
python3 build.py                    # wipe and rebuild _site/
python3 build.py --serve            # build, then serve _site/ on http://localhost:8000
python3 tools/fetch_images.py       # one-off: download old WordPress images into static/img/wp/
```

There are no tests or linters. Verify changes by building and inspecting the generated HTML in `_site/` (the build prints a page/post count).

## Architecture

Everything happens in `build.py`'s `main()`, top to bottom. Content types and how each is rendered:

| Source | Template | Notes |
| --- | --- | --- |
| `content/site.yml` | (global `site`) | Company facts, nav, `redirects`, `form_action`, `featured_clients`. Feeds every page, footer, JSON-LD, `llms.txt` |
| `content/home.yml` | `home.html` | Homepage copy, laid out like a sales conversation: hero with `intents` chips (anchor links to the `paths`), `why` tiles, `hero_stats`, client logos, problem/fix `paths` (crm, payroll, sms; each `art` names `static/img/illus/<art>.svg`), CRM `migration` band, `steps`, FAQs, latest posts; the enquiry form comes from `base.html`. `{years}`/`{founded}` in `why` text are filled in from `site.founded` (`years` is computed in `build.py`). Each CTA's `interest` must exactly match an `<option>` in `_form.html`: `site.js` pre-selects it on click via `data-interest` |
| `content/services/*.md` | `service.html` | Sorted by `order`; `related_cat` pulls related blog posts; `answer`, `glance`, `features`, `faqs` front matter; optional `image`/`image_alt` (also on pages) shows a banner beside the H1 and becomes og:image and `primaryImageOfPage`; `{{zoho_signup}}` placeholder replaced in the body |
| `content/pages/*.md` | `template:` front matter (default `page.html`) | `schema_type`, `priority`, `noindex`, `hide_band` |
| `content/blog/*.md` | `post.html` / `blog_index.html` | See blog rules below |
| `content/clients.yml` | `_clients.html` partial | Ordered by `site.featured_clients`; a client whose logo isn't downloaded locally shows its name instead of a broken image |
| (hard-coded in build.py) | `contact.html`, `sitemap_page.html`, `page.html` (for `404.html`), `redirect.html` | Contact, blog index, site map and 404 copy live in `build.py`, not content files |

Key behaviours that span files:

- **URLs come from front matter `url`**, not filenames. Blog posts kept their original WordPress URLs (`/blog/<slug>/`), the blog index is `/blogs/`. Each URL is written as `<url>/index.html`. Old URLs that should forward are listed under `redirects` in `site.yml` and rendered as meta-refresh pages via `redirect.html`.
- **Blog categories** (`payroll`, `sms`, `crm`, `company`) are inferred by `categorise()` from keywords in the URL and title unless `category` is set in front matter. Keyword checks run in order (sms/alert/messaging → bigin/crm → payroll/attendance/leave → company), so a title like "payroll alerts" lands in `sms`; set `category` explicitly when that's wrong. The category drives related posts, the CTA block (`svc_by_cat` / `cta_text`), and which service page lists the post (via its `related_cat`). Adding a new category means updating `CATS`, `svc_by_cat` and `cta_text` together, or the build raises a `KeyError`. `author` is a key into the `AUTHORS` dict.
- **Blog FAQ schema** is auto-extracted by `extract_faqs()` from a `## Frequently Asked Questions` section with `###`/`####` question headings. A leading `# H1` in a post body is stripped because the template supplies the H1.
- **Images**: `asset()` rewrites old `zensys.in/wp-content/uploads/...` and `zensys.in/resources/img/...` URLs to `/assets/img/wp/<path_with_underscores>` only if the local file exists in `static/img/wp/`; otherwise the remote URL is kept. Applies to front-matter `image`, client logos, and Markdown images in bodies.
- **Static files**: `static/` is copied to `_site/assets/` (so templates reference `/assets/...`); `static/root/*` plus `CNAME` and `.nojekyll` go to the site root.
- **Base path**: templates and content use root-relative links (`/assets/...`, `/blog/...`). If the `BASE_PATH` env var is set (e.g. `/zensys-site`), `apply_base_path()` prefixes them (`href`, `src`, `action`, every URL in `srcset`, CSS `url()`, meta refresh) in the built HTML/CSS as a final pass, so the site also works at `<user>.github.io/<repo>/`. Any new attribute that holds root-relative URLs must be added to that function too, or it 404s under a base path. The workflow takes it from `actions/configure-pages`, which returns an empty value once the custom domain is configured. Absolute URLs (canonical, OG, JSON-LD, sitemap) always use `site.url`. Keep new links root-relative and don't hard-code the prefix. `--serve` serves at the root, so build without `BASE_PATH` for local preview.
- **JSON-LD**: every page gets an `@graph` built from `org_node`, `website_node`, plus page-specific nodes (Service, BlogPosting, BreadcrumbList, FAQPage, etc.), rendered into `base.html` as `page.jsonld`.
- **Generated extras**: `sitemap.xml` (+ `sitemap_index.xml` at the old Yoast path), `robots.txt` explicitly allowing named AI crawlers, `llms.txt` / `llms-full.txt` (built from services, posts, and raw service Markdown), and `feed.xml`.
- **Templates** use Jinja2 with autoescape, `trim_blocks`/`lstrip_blocks`, and an `md` filter for Markdown in YAML fields. Partials are prefixed with `_`. Colours come from the logo (`static/img/Zensys-logo-new.png`) and are tokens at the top of `site.css`: red `--red` for actions and highlights (primary buttons, focus, active nav), indigo `--brand` for links and structure, slate `--ink` for headings. Don't add colours outside the logo palette, apart from functional green for ticks. The layout is the "classic" design: Schibsted throughout, bold left-aligned section heads, white cards with light borders on alternating grey sections, pill buttons, and a sticky floating header: a white pill 12px below the top (logo, Zoho partner badge with a CSS shine, semibold nav, the last nav item "Contact us" as a red pill via `.nav-cta`), with a red underline that slides in on hover and marks the active item, chevrons on items with dropdowns, and a stronger shadow added by `site.js` once the page scrolls. The header stays a white pill on every page and hero so the logo always shows in its original colours (never make it transparent or recolour the logo). The homepage hero has a negative top margin so it slides up behind the header; keep the two in step if the header height changes. The homepage hero has two styles, picked by `hero_style` in `home.yml`: `fluid` (current) is a deep indigo hero with blob shapes, text on the left and a large team photo on the right (`hero-team-*`, Pexels 3932229) in a rounded frame with `hero_badges` floating on it; `cloud` is a plain indigo gradient with soft glows (no blobs), with a centred headline, a partner pill above it and the `hero_cloud` product badges as small translucent pills (icon + name; own icons from the `cloud_icon` macro, no Zoho product logos; some smaller and fainter for depth) floating around it on wide screens and wrapping into a row below on narrow ones; `cards` is an indigo gradient with the text centred and a fan of five tilted photo cards (`hero_cards`) cut off by its bottom edge. Both show the `h1_highlight` phrase in a light tint of the logo red. Alternative Apple-style and Techvolt-style designs are parked in `.variants/` (and the pre-redesign copy in `.backup/`); the build doesn't use them. `site.js` defers analytics (Zoho PageSense) and chat (SalesIQ) until user interaction; there is no jQuery or framework.

## Content conventions

- New blog post: copy an existing file in `content/blog/` and set `url`, `title`, `meta_title`, `description`, `date`, `author`, `image` (optional `updated`, `image_alt`, `category`). `" | Zensys"` is appended to blog `meta_title` automatically.
- Prefer editing YAML/Markdown content over changing `build.py`. Never edit `_site/` (build output, gitignored). `AGENTS.md` holds the same guidance for other agents; keep the two consistent.
- Photos live in `static/img/photos/` with 800/1400/2200px copies for `srcset`. The homepage hero cards are single 570x760 portrait crops from Pexels (Pexels License, no attribution needed): 4307856 (`hero-remote`), 8297044 (`hero-accounts`), 16659308 (`hero-laptop-smile`), 7129065 (`hero-phone`), 18890945 (`hero-office`). The old hero background `open-office-*` (Pexels 9497770) is no longer used. The "Why businesses choose Zensys" tiles use Pexels 39351264 (`why-sectors`), 577210 (`why-custom`), 4963448 (`why-years`) and 7698826 (`why-team`). The problem/fix blocks use line-art SVGs drawn for Zensys in the logo palette (`static/img/illus/payroll.svg`, `sms.svg`, `crm.svg`); keep new illustrations in the same style (navy outlines, indigo/red fills, light blob behind). Never caption stock people as Zensys staff or clients.
- Products are always presented in the order **CRM (Bigin/Zoho), payroll, SMS**: nav, footer, homepage, form options, service `order`, blog categories (`CATS`), meta text and lists. Keep new copy in that order.
- Contact details (phone, email, address) should only be changed in `site.yml`; they propagate everywhere, including structured data.
- The enquiry form posts to `form_action` in `site.yml`; when empty it falls back to a `mailto:` with the enquiry pre-filled (GitHub Pages can't send email).
- Outstanding pre-launch TODOs (opening hours, `same_as` social links, legal name, form endpoint, logo) are listed in `README.md` and as comments in `site.yml`.
