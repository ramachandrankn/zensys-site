# zensys.in

The Zensys website: a fast static site built from Markdown and YAML, hosted free on GitHub Pages, set up for Google search (SEO) and AI answer engines (AEO).

## What's in here

| Folder / file | What it is |
| --- | --- |
| `content/site.yml` | Company details used everywhere: phone, email, address, nav, redirects, form endpoint |
| `content/home.yml` | Homepage text: visitor problems and fixes, CRM migration, reasons to choose Zensys, FAQs |
| `content/services/*.md` | One file per product page (Bigin CRM, Zoho partner, payroll on-premises, cloud payroll, SMS; `order` follows CRM, payroll, SMS) |
| `content/pages/*.md` | About, privacy, cookies, terms |
| `content/blog/*.md` | Blog posts, one Markdown file each (45 migrated from WordPress with their original URLs) |
| `content/clients.yml` | Client names and logos |
| `templates/` | Page layouts (HTML with Jinja2) |
| `static/` | CSS, JavaScript, fonts, images |
| `build.py` | Turns all of the above into the finished site in `_site/` |
| `tools/fetch_images.py` | One-time copy of images from the old WordPress server |

## Go live on GitHub Pages

1. **Create the repo.** On GitHub, create a new repository (e.g. `zensys-site`) and push this folder to the `main` branch.
2. **Turn on Pages.** Repo → Settings → Pages → *Build and deployment* → Source: **GitHub Actions**. The included workflow (`.github/workflows/deploy.yml`) builds and publishes the site on every push. Check the Actions tab: the first run takes about a minute. Until the custom domain is set, the site is live at `https://<github-username>.github.io/<repo>/`. The build detects the subfolder and fixes the links, so you can review everything there before touching DNS.
3. **Copy any remaining images (before switching DNS).** All images have already been copied into `static/img/wp/` except the Alcatel-Lucent client logo (the old server no longer has it; its tile shows the company name instead). If you add content that points at the old server, run this on any computer with Python and internet:
   ```
   pip install -r requirements.txt
   python3 tools/fetch_images.py
   python3 build.py
   git add -A && git commit -m "Bring images in-house" && git push
   ```
   Run it while the WordPress site is still live. Anything it can't download simply keeps loading from the old URL until it's replaced.
4. **Point the domain.** Repo → Settings → Pages → Custom domain: `zensys.in`, then tick **Enforce HTTPS** once it's offered. In the DNS settings (Cloudflare or wherever the domain is managed):
   - `A` records for `zensys.in` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `CNAME` for `www` → `<github-username>.github.io`
   - If DNS is on Cloudflare, set these records to **DNS only** (grey cloud) until GitHub has issued the HTTPS certificate.
5. **Let AI crawlers in.** If the domain stays on Cloudflare, go to Security → Bots and turn **off** "Block AI bots" / "AI Scrapers and Crawlers". The current site blocks ChatGPT, Claude and Perplexity at this layer, so they can't read or cite it. The new `robots.txt` explicitly allows them.
6. **Tell Google.** In Google Search Console, submit `https://zensys.in/sitemap.xml` and use URL Inspection on the homepage and service pages. Update the Google Business Profile website link if needed.

## Before launch: please check

- **Opening hours** — add them in `content/site.yml` (`hours` and `hours_human`).
- **Social profiles** — add LinkedIn / Facebook / Google Business Profile URLs to `same_as` in `content/site.yml`. These help Google and AI tools confirm who Zensys is.
- **Enquiry form** — GitHub Pages can't send email. Until you add an endpoint, the form opens the visitor's email app with the enquiry pre-filled. For direct delivery into Zoho, create a Zoho Forms form or a Bigin Web-to-Contact form and paste its action URL into `form_action` in `content/site.yml`.
- **Legal pages** — `privacy`, `cookies-policy` and `terms-of-use` were rewritten to match the new site (Zoho PageSense, SalesIQ, no WordPress). Have them reviewed.
- **SMS since 2007 vs company since 2008** — the old site says both. The new site keeps "SMS services since 2007" and "founded 2008". Correct either if needed.
- **Logo** — the header and footer use the Zensys mark `static/img/zensys-mark.png` next to the name. To use a different logo file, replace that image (or change the `<img>` inside `<a class="brand">` in `templates/base.html`).
- **Alcatel-Lucent logo** — missing from the old server, so its client tile shows the name. Add the logo as `static/img/wp/Alcatel-Logo.jpeg` to show it.

## Everyday edits

- **New blog post:** copy any file in `content/blog/`, change the front matter (`url`, `title`, `meta_title`, `description`, `date`, `author`, `image`) and write the post in Markdown. End with a `## Frequently Asked Questions` section using `####` questions to get FAQ rich results automatically. Push, and it's live in about a minute.
- **Change phone, email or address:** edit `content/site.yml` once; every page, the footer and the structured data update together.
- **Preview locally:** `python3 build.py --serve` then open http://localhost:8000.

## What the build generates for SEO and AEO

- Clean titles, meta descriptions, canonical URLs, Open Graph and Twitter cards on every page
- JSON-LD structured data: Organization / ProfessionalService with address and contact, WebSite, Service, BlogPosting, BreadcrumbList, FAQPage, AboutPage, ContactPage
- A short "answer box" at the top of each service page so search and AI tools can quote a direct answer
- `sitemap.xml` (plus `sitemap_index.xml` at the old Yoast address), `robots.txt`, `feed.xml`
- `llms.txt` and `llms-full.txt` summarising the company and every page for AI assistants
- Old WordPress URLs kept as-is; retired ones (`/blog/`, `/author/...`, `/page/2/`, the duplicate Zoho partner page) forward to their new home
- No page builder, no jQuery: pages are small, and analytics and chat load only after the visitor interacts
