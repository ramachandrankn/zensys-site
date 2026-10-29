#!/usr/bin/env python3
"""
Zensys static site builder.

    pip install -r requirements.txt
    python3 build.py            # builds into _site/
    python3 build.py --serve    # builds, then serves on http://localhost:8000

Content lives in content/ (YAML + Markdown). Templates in templates/.
Nothing here needs editing for day-to-day changes: add a blog post by dropping a
Markdown file into content/blog/ and pushing to GitHub.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
OUT = ROOT / "_site"
# Set when the site is served from a subfolder, e.g. https://<user>.github.io/<repo>/
# before the custom domain is live. The deploy workflow fills it in automatically.
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")

MD = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"],
                       extension_configs={"smarty": {"smart_quotes": False}})


def md(text: str) -> str:
    MD.reset()
    return MD.convert(text or "")


def read_front_matter(path: Path):
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        return yaml.safe_load(fm) or {}, body.strip()
    return {}, raw.strip()


def parse_date(v):
    if not v:
        return None
    if isinstance(v, dt.datetime):
        return v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day, tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def human_date(d):
    return f"{d.day} {d.strftime('%B %Y')}" if d else ""


# ----------------------------------------------------------------- images
WP_IMG_DIR = STATIC / "img" / "wp"


def asset(url: str) -> str:
    """Old WordPress images: use the local copy if tools/fetch_images.py has
    downloaded it, otherwise keep pointing at the old URL."""
    if not url:
        return url
    m = re.match(r"https?://(?:www\.)?zensys\.in/(?:wp-content/uploads|resources/img)/(.+)$", url)
    if m:
        local = WP_IMG_DIR / m.group(1).replace("/", "_")
        if local.exists():
            return "/assets/img/wp/" + local.name
    return url


def rewrite_body_images(text: str) -> str:
    return re.sub(r"(!\[[^\]]*\]\()([^)]+)(\))", lambda m: m.group(1) + asset(m.group(2)) + m.group(3), text)


# ----------------------------------------------------------------- blog
CATS = {  # display order: CRM, payroll, SMS
    "crm": "CRM",
    "payroll": "Payroll",
    "sms": "SMS",
    "company": "Company",
}
AUTHORS = {"admin": "Zensys Team", "kaviyarasan": "Kaviyarasan", "swetha": "Swetha", "prakash": "Prakash"}


def categorise(url, title):
    s = (url + " " + title).lower()
    if "sms" in s or "alert" in s or "messaging" in s:
        return "sms"
    if "bigin" in s or "crm" in s:
        return "crm"
    if "payroll" in s or "attendance" in s or "leave" in s:
        return "payroll"
    return "company"


def extract_faqs(body: str):
    """Pull Q&A pairs from a 'Frequently Asked Questions' section written as
    #### Question / answer paragraphs."""
    m = re.search(r"^##\s+Frequently Asked Questions[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.S | re.M)
    if not m:
        return []
    faqs = []
    for q, a in re.findall(r"^#{3,4}\s+(.+?)\n+(.*?)(?=^#{3,4}\s|\Z)", m.group(1), re.S | re.M):
        a = a.strip()
        if a:
            faqs.append({"q": q.strip(), "a": a})
    return faqs


def load_posts(site):
    posts = []
    for p in sorted((CONTENT / "blog").glob("*.md")):
        fm, body = read_front_matter(p)
        url = fm.get("url") or f"/blog/{p.stem}/"
        title = fm["title"]
        cat = fm.get("category") or categorise(url, title)
        pub = parse_date(fm.get("date"))
        upd = parse_date(fm.get("updated")) or pub
        author_key = str(fm.get("author", "admin")).lower()
        body = rewrite_body_images(body)
        words = len(re.findall(r"\w+", body))
        posts.append({
            "slug": p.stem,
            "url": url,
            "title": title,
            "meta_title": fm.get("meta_title") or title,
            "description": fm.get("description", ""),
            "image": "" if "zensys-webpage-scaled" in fm.get("image", "") else asset(fm.get("image", "")),
            "image_alt": fm.get("image_alt") or title,
            "published_dt": pub,
            "updated_dt": upd,
            "date_human": human_date(pub),
            "updated_human": human_date(upd) if upd and pub and (upd - pub).days >= 2 else "",
            "author": AUTHORS.get(author_key, fm.get("author", "Zensys Team")),
            "cat": cat,
            "cat_label": CATS[cat],
            "body": body,
            "faqs": extract_faqs(body),
            "read_min": max(1, round(words / 220)),
        })
    posts.sort(key=lambda x: x["published_dt"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True)
    return posts


# ----------------------------------------------------------------- schema
def org_node(site):
    a = site["address"]
    addr = {"@type": "PostalAddress", "addressLocality": a["locality"], "addressRegion": a["region"], "addressCountry": a["country"]}
    if a.get("street"):
        addr["streetAddress"] = a["street"]
    if a.get("postal_code"):
        addr["postalCode"] = a["postal_code"]
    node = {
        "@type": ["Organization", "ProfessionalService"],
        "@id": site["url"] + "/#organization",
        "name": site["name"],
        "legalName": site["legal_name"],
        "url": site["url"] + "/",
        "logo": {"@type": "ImageObject", "url": site["url"] + "/assets/img/logo.png"},
        "image": site["url"] + "/assets/img/og-default.png",
        "description": " ".join(site["summary"].split()),
        "foundingDate": site["founded"],
        "telephone": site["phone_e164"],
        "email": site["email"],
        "address": addr,
        "areaServed": [{"@type": "Place", "name": n} for n in site["areas_served"]],
        "knowsAbout": ["Bigin by Zoho CRM", "Zoho implementation", "CRM data migration", "Payroll software",
                       "Statutory compliance (PF, ESI, PT, TDS)", "Biometric attendance", "Bulk SMS", "Transactional SMS and OTP"],
        "contactPoint": [{"@type": "ContactPoint", "telephone": site["phone_e164"], "email": site["email"],
                          "contactType": "sales", "areaServed": "IN", "availableLanguage": ["en", "ta"]}],
        "priceRange": "₹₹",
    }
    if site.get("hours"):
        node["openingHours"] = site["hours"]
    if site.get("same_as"):
        node["sameAs"] = site["same_as"]
    return node


def website_node(site):
    return {"@type": "WebSite", "@id": site["url"] + "/#website", "url": site["url"] + "/", "name": site["name"],
            "publisher": {"@id": site["url"] + "/#organization"}, "inLanguage": "en-IN"}


def crumbs_node(site, crumbs):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": c["name"], "item": site["url"] + c["url"]}
        for i, c in enumerate(crumbs)]}


def faq_node(faqs):
    def plain(s):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", md(s))).strip()
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": plain(f["a"])}}
        for f in faqs]}


def apply_base_path():
    """Prefix root-relative links in the built HTML and CSS with BASE_PATH.
    Absolute URLs (canonical, Open Graph, JSON-LD, sitemap) keep pointing at site.url."""
    if not BASE_PATH:
        return
    attr = re.compile(r'(\s(?:href|src|action)=["\'])/(?!/)')
    refresh = re.compile(r'(http-equiv="refresh" content="\d+;\s*url=)/(?!/)')
    css_url = re.compile(r'(url\(["\']?)/(?!/)')
    srcset = re.compile(r'(\ssrcset=")([^"]*)"')
    srcset_url = re.compile(r'(^|,\s*)/(?!/)')
    for f in OUT.rglob("*.html"):
        t = f.read_text(encoding="utf-8")
        t = attr.sub(rf"\1{BASE_PATH}/", t)
        t = srcset.sub(lambda m: m.group(1) + srcset_url.sub(rf"\1{BASE_PATH}/", m.group(2)) + '"', t)
        t = refresh.sub(rf"\1{BASE_PATH}/", t)
        t = css_url.sub(rf"\1{BASE_PATH}/", t)
        f.write_text(t, encoding="utf-8")
    for f in OUT.rglob("*.css"):
        f.write_text(css_url.sub(rf"\1{BASE_PATH}/", f.read_text(encoding="utf-8")), encoding="utf-8")


def graph(*nodes):
    return json.dumps({"@context": "https://schema.org", "@graph": [n for n in nodes if n]}, ensure_ascii=False, indent=1)


# ----------------------------------------------------------------- build
def main():
    site = yaml.safe_load((CONTENT / "site.yml").read_text(encoding="utf-8"))
    home = yaml.safe_load((CONTENT / "home.yml").read_text(encoding="utf-8"))
    clients = yaml.safe_load((CONTENT / "clients.yml").read_text(encoding="utf-8"))
    for c in clients:
        c["logo_src"] = asset(c["logo"])
    feat = site.get("featured_clients", [])
    clients.sort(key=lambda c: feat.index(c["name"]) if c["name"] in feat else len(feat))
    a = site["address"]
    site["address_line"] = ", ".join(x for x in [a.get("street"), a.get("locality"), a.get("region"), a.get("postal_code")] if x)
    site["hours_human"] = site.get("hours_human", "")
    now = dt.datetime.now(dt.timezone.utc)
    build_id = now.strftime("%Y%m%d%H%M")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["md"] = lambda s: Markup(md(s))
    env.globals.update(site=site, year=now.year, build_id=build_id, clients=clients)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(STATIC, OUT / "assets")
    for extra in ["CNAME", ".nojekyll"]:
        if (ROOT / extra).exists():
            shutil.copy(ROOT / extra, OUT / extra)
    for f in (STATIC / "root").glob("*"):
        shutil.copy(f, OUT / f.name)
    shutil.rmtree(OUT / "assets" / "root", ignore_errors=True)

    sitemap = []  # (url, lastmod, priority)

    def write(url, html_text):
        path = OUT / url.strip("/") / "index.html" if url != "/" else OUT / "index.html"
        if url.endswith(".html"):
            path = OUT / url.strip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html_text, encoding="utf-8")

    def page_obj(**kw):
        p = {"og_image": site["url"] + "/assets/img/og-default.png", "noindex": False}
        p.update(kw)
        if p.get("image"):
            p["og_image"] = p["image"] if p["image"].startswith("http") else site["url"] + p["image"]
        p["canonical"] = site["url"] + p["url"]
        return p

    posts = load_posts(site)
    for p in posts:
        p["published"] = p["published_dt"].isoformat() if p["published_dt"] else ""
        p["modified"] = p["updated_dt"].isoformat() if p["updated_dt"] else ""

    # ---------------- services
    services = []
    for f in sorted((CONTENT / "services").glob("*.md")):
        fm, body = read_front_matter(f)
        fm["slug"] = f.stem
        body = body.replace("{{zoho_signup}}", site["zoho_signup_url"])
        fm["body_html"] = md(rewrite_body_images(body))
        fm["glance"] = [(k, v) for d in fm.get("glance", []) for k, v in d.items()]
        services.append(fm)
    services.sort(key=lambda s: s.get("order", 99))
    for s in services:
        rel = [p for p in posts if p["cat"] == s.get("related_cat")][:5]
        crumbs = [{"name": "Home", "url": "/"}, {"name": s.get("crumb", s["h1"]), "url": s["url"]}]
        svc = {
            "@type": "Service", "@id": site["url"] + s["url"] + "#service", "name": s["service_name"],
            "serviceType": s.get("service_type", s["service_name"]), "description": s["description"],
            "provider": {"@id": site["url"] + "/#organization"},
            "areaServed": [{"@type": "Place", "name": n} for n in site["areas_served"]],
            "url": site["url"] + s["url"],
        }
        webpage = {"@type": "WebPage", "@id": site["url"] + s["url"], "url": site["url"] + s["url"], "name": s["meta_title"],
                   "isPartOf": {"@id": site["url"] + "/#website"}, "about": {"@id": site["url"] + s["url"] + "#service"},
                   "dateModified": now.date().isoformat(), "inLanguage": "en-IN"}
        page = page_obj(url=s["url"], meta_title=s["meta_title"], description=s["description"], h1=s["h1"],
                        lede=s.get("lede"), answer=s.get("answer"), features=s.get("features"),
                        features_title=s.get("features_title"), body_html=s["body_html"], faqs=s.get("faqs"),
                        glance=s["glance"], related_posts=rel, crumbs=crumbs, section=s.get("section", s["url"]),
                        image=asset(s.get("image", "")), image_alt=s.get("image_alt", ""))
        if page["image"]:
            svc["image"] = webpage["primaryImageOfPage"] = page["og_image"]
        page["jsonld"] = graph(org_node(site), website_node(site), webpage, svc, crumbs_node(site, crumbs),
                               faq_node(s["faqs"]) if s.get("faqs") else None)
        write(s["url"], env.get_template("service.html").render(page=page))
        sitemap.append((s["url"], now.date().isoformat(), "0.9"))

    # ---------------- home
    crumbs = [{"name": "Home", "url": "/"}]
    page = page_obj(url="/", meta_title=home["meta_title"], description=home["description"], crumbs=crumbs)
    homepage = {"@type": "WebPage", "@id": site["url"] + "/", "url": site["url"] + "/", "name": home["meta_title"],
                "isPartOf": {"@id": site["url"] + "/#website"}, "about": {"@id": site["url"] + "/#organization"},
                "inLanguage": "en-IN"}
    page["jsonld"] = graph(org_node(site), website_node(site), homepage, faq_node(home["faqs"]))
    write("/", env.get_template("home.html").render(page=page, home=home, latest=posts[:3],
                                                   years=now.year - int(site["founded"])))
    sitemap.append(("/", now.date().isoformat(), "1.0"))

    # ---------------- simple pages (about, legal)
    for f in sorted((CONTENT / "pages").glob("*.md")):
        fm, body = read_front_matter(f)
        crumbs = [{"name": "Home", "url": "/"}, {"name": fm.get("crumb", fm["h1"]), "url": fm["url"]}]
        page = page_obj(url=fm["url"], meta_title=fm["meta_title"], description=fm["description"], h1=fm["h1"],
                        lede=fm.get("lede"), body_html=md(body), faqs=fm.get("faqs"), crumbs=crumbs,
                        noindex=fm.get("noindex", False), hide_band=fm.get("hide_band", False),
                        image=asset(fm.get("image", "")), image_alt=fm.get("image_alt", ""))
        ptype = fm.get("schema_type", "WebPage")
        node = {"@type": ptype, "@id": site["url"] + fm["url"], "url": site["url"] + fm["url"], "name": fm["meta_title"],
                "isPartOf": {"@id": site["url"] + "/#website"}, "about": {"@id": site["url"] + "/#organization"}}
        if page["image"]:
            node["primaryImageOfPage"] = page["og_image"]
        page["jsonld"] = graph(org_node(site), website_node(site), node, crumbs_node(site, crumbs),
                               faq_node(fm["faqs"]) if fm.get("faqs") else None)
        write(fm["url"], env.get_template(fm.get("template", "page.html")).render(page=page))
        sitemap.append((fm["url"], now.date().isoformat(), fm.get("priority", "0.5")))

    # ---------------- contact
    crumbs = [{"name": "Home", "url": "/"}, {"name": "Contact", "url": "/contact-us/"}]
    page = page_obj(url="/contact-us/", meta_title="Contact Zensys | Zoho CRM, Payroll & SMS in Chennai",
                    description=f"Call {site['phone']} or send your requirement for Bigin by Zoho CRM, payroll software or bulk SMS. Zensys, {site['address_line']}.",
                    h1="Talk to Zensys", lede="Tell us about your CRM, payroll or SMS requirement. We’ll suggest the right setup and arrange a demo.",
                    crumbs=crumbs, hide_band=True)
    node = {"@type": "ContactPage", "@id": site["url"] + "/contact-us/", "url": site["url"] + "/contact-us/",
            "name": page["meta_title"], "about": {"@id": site["url"] + "/#organization"}, "isPartOf": {"@id": site["url"] + "/#website"}}
    page["jsonld"] = graph(org_node(site), website_node(site), node, crumbs_node(site, crumbs))
    write("/contact-us/", env.get_template("contact.html").render(page=page))
    sitemap.append(("/contact-us/", now.date().isoformat(), "0.8"))

    # ---------------- blog
    cats = [{"key": k, "label": v, "count": sum(1 for p in posts if p["cat"] == k)} for k, v in CATS.items()]
    cats = [c for c in cats if c["count"]]
    crumbs = [{"name": "Home", "url": "/"}, {"name": "Blog", "url": "/blogs/"}]
    page = page_obj(url="/blogs/", meta_title="Blog: CRM, Payroll & SMS Guides for Indian Businesses | Zensys",
                    description="Practical guides on Bigin by Zoho CRM, payroll compliance (PF, ESI, PT, TDS), and bulk and transactional SMS for Indian businesses.",
                    h1="Guides on CRM, payroll and SMS", lede="Written by the Zensys team for HR, finance and sales teams in India.",
                    crumbs=crumbs)
    node = {"@type": "CollectionPage", "@id": site["url"] + "/blogs/", "url": site["url"] + "/blogs/", "name": page["meta_title"],
            "isPartOf": {"@id": site["url"] + "/#website"},
            "mainEntity": {"@type": "ItemList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": site["url"] + p["url"]} for i, p in enumerate(posts)]}}
    page["jsonld"] = graph(org_node(site), website_node(site), node, crumbs_node(site, crumbs))
    write("/blogs/", env.get_template("blog_index.html").render(page=page, posts=posts, cats=cats))
    sitemap.append(("/blogs/", now.date().isoformat(), "0.7"))

    svc_by_cat = {"payroll": ("/service/payroll-software-on-premises/", "See payroll software"),
                  "sms": ("/service/sms-software/", "See SMS software"),
                  "crm": ("/service/bigin-by-zoho-crm/", "See Bigin by Zoho CRM"),
                  "company": ("/contact-us/", "Book a free consultation")}
    cta_text = {"payroll": "Zensys has completed 200+ payroll installations since 2008. We can show you the software on your own pay structure.",
                "sms": "Send OTPs, alerts and campaigns through a platform with delivery reports and integration with your CRM or ERP.",
                "crm": "As an authorized Zoho partner, we set up, customise and support Bigin for your sales process.",
                "company": "Tell us what you need and we’ll recommend the right mix of CRM, payroll and SMS."}
    for p in posts:
        crumbs = [{"name": "Home", "url": "/"}, {"name": "Blog", "url": "/blogs/"}, {"name": p["title"], "url": p["url"]}]
        body = re.sub(r"^#\s+.*\n", "", p["body"])  # the page already has an H1
        related = [q for q in posts if q["cat"] == p["cat"] and q["url"] != p["url"]][:3]
        cta_url, cta_label = svc_by_cat[p["cat"]]
        page = page_obj(url=p["url"], meta_title=p["meta_title"] + " | Zensys", description=p["description"],
                        h1=p["title"], body_html=md(body), og_type="article",
                        og_image=p["image"] if p["image"].startswith("http") else site["url"] + p["image"] if p["image"] else site["url"] + "/assets/img/og-default.png",
                        published=p["published"], modified=p["modified"], crumbs=crumbs, image=p["image"],
                        image_alt=p["image_alt"], author=p["author"], date_human=p["date_human"],
                        updated_human=p["updated_human"], read_min=p["read_min"], cat_label=p["cat_label"],
                        related=related, cta_url=cta_url, cta_label=cta_label, cta_text=cta_text[p["cat"]],
                        section="/blogs/")
        art = {"@type": "BlogPosting", "@id": site["url"] + p["url"] + "#article", "headline": p["title"][:110],
               "description": p["description"], "datePublished": p["published"], "dateModified": p["modified"],
               "author": {"@type": "Organization" if p["author"] == "Zensys Team" else "Person", "name": p["author"],
                          **({"url": site["url"] + "/about-us/"} if p["author"] == "Zensys Team" else {})},
               "publisher": {"@id": site["url"] + "/#organization"},
               "mainEntityOfPage": site["url"] + p["url"], "inLanguage": "en-IN",
               "articleSection": p["cat_label"], "wordCount": len(re.findall(r"\w+", p["body"]))}
        if p["image"]:
            art["image"] = page["og_image"]
        page["jsonld"] = graph(org_node(site), website_node(site), art, crumbs_node(site, crumbs),
                               faq_node(p["faqs"]) if p["faqs"] else None)
        write(p["url"], env.get_template("post.html").render(page=page))
        sitemap.append((p["url"], (p["updated_dt"] or now).date().isoformat(), "0.6"))

    # ---------------- html sitemap
    crumbs = [{"name": "Home", "url": "/"}, {"name": "Site map", "url": "/site-map/"}]
    page = page_obj(url="/site-map/", meta_title="Site map | Zensys", description="Every page on zensys.in.", h1="Site map", crumbs=crumbs)
    page["jsonld"] = graph(org_node(site), website_node(site), crumbs_node(site, crumbs))
    write("/site-map/", env.get_template("sitemap_page.html").render(page=page, services=services, posts=posts, cats=cats))
    sitemap.append(("/site-map/", now.date().isoformat(), "0.3"))

    # ---------------- 404
    page = page_obj(url="/404.html", meta_title="Page not found | Zensys", description="This page doesn't exist.",
                    h1="We couldn’t find that page", lede="It may have moved when we rebuilt the site. Try one of these instead.",
                    body_html=md("- [Bigin by Zoho CRM](/service/bigin-by-zoho-crm/)\n- [Payroll software](/service/payroll-software-on-premises/)\n- [Bulk SMS](/service/sms-software/)\n- [Blog](/blogs/)\n- [Contact us](/contact-us/)"),
                    crumbs=[{"name": "Home", "url": "/"}, {"name": "Not found", "url": "/404.html"}], noindex=True)
    page["jsonld"] = graph(website_node(site))
    (OUT / "404.html").write_text(env.get_template("page.html").render(page=page), encoding="utf-8")

    # ---------------- redirects from old URLs
    for old, new in (site.get("redirects") or {}).items():
        write(old, env.get_template("redirect.html").render(target=new, target_abs=site["url"] + new))

    # ---------------- sitemap.xml
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod, prio in sitemap:
        lines.append(f"  <url><loc>{xml_escape(site['url'] + url)}</loc><lastmod>{lastmod}</lastmod><priority>{prio}</priority></url>")
    lines.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # keep the old Yoast sitemap URL working for Search Console
    (OUT / "sitemap_index.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <sitemap><loc>{site["url"]}/sitemap.xml</loc><lastmod>{now.date().isoformat()}</lastmod></sitemap>\n</sitemapindex>\n',
        encoding="utf-8")

    # ---------------- robots.txt (search and AI crawlers explicitly welcome)
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
               "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot", "CCBot",
               "meta-externalagent", "Amazonbot", "DuckAssistBot"]
    robots = ["# Zensys welcomes search engines and AI assistants.", "User-agent: *", "Allow: /", ""]
    for b in ai_bots:
        robots += [f"User-agent: {b}", "Allow: /", ""]
    robots += [f"Sitemap: {site['url']}/sitemap.xml", ""]
    (OUT / "robots.txt").write_text("\n".join(robots), encoding="utf-8")

    # ---------------- llms.txt  (https://llmstxt.org)
    L = [f"# {site['name']}", "", f"> {' '.join(site['summary'].split())}", "",
         f"- Phone / WhatsApp: {site['phone']}", f"- Email: {site['email']}",
         f"- Address: {site['address_line']}", f"- Founded: {site['founded']}", "",
         "## Products and services", ""]
    for s in services:
        L.append(f"- [{s['service_name']}]({site['url']}{s['url']}): {s['description']}")
    L += ["", "## Company", "", f"- [About Zensys]({site['url']}/about-us/): history, Zoho partnership, clients",
          f"- [Contact]({site['url']}/contact-us/): phone, email, office address, enquiry form", "",
          "## Guides", ""]
    for p in posts:
        L.append(f"- [{p['title']}]({site['url']}{p['url']}): {p['description']}")
    L += ["", "## Optional", "", f"- [Full text of service pages]({site['url']}/llms-full.txt)", ""]
    (OUT / "llms.txt").write_text("\n".join(L), encoding="utf-8")

    full = [f"# {site['name']}: full service information", "", " ".join(site["summary"].split()), ""]
    for s in services:
        src = (CONTENT / "services" / f"{s['slug']}.md").read_text(encoding="utf-8").split("---", 2)[2]
        full += [f"## {s['h1']}", f"URL: {site['url']}{s['url']}", "", s["description"], ""]
        if s.get("answer"):
            full += [s["answer"].strip(), ""]
        for f in s.get("features") or []:
            full.append(f"- {f['t']}: {f['d']}")
        full += ["", src.strip().replace("{{zoho_signup}}", site["zoho_signup_url"]), ""]
        for f in s.get("faqs") or []:
            full += [f"Q: {f['q']}", f"A: {' '.join(f['a'].split())}", ""]
    full += ["## Clients", "", ", ".join(c["name"] for c in clients), ""]
    (OUT / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

    # ---------------- RSS
    items = []
    for p in posts[:30]:
        items.append(
            f"<item><title>{xml_escape(p['title'])}</title><link>{site['url']}{p['url']}</link>"
            f"<guid>{site['url']}{p['url']}</guid><pubDate>{p['published_dt'].strftime('%a, %d %b %Y %H:%M:%S %z')}</pubDate>"
            f"<description>{xml_escape(p['description'])}</description></item>")
    (OUT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>{site['name']} blog</title><link>{site['url']}/blogs/</link>"
        f"<description>{xml_escape(site['tagline'])}</description><language>en-in</language>"
        + "".join(items) + "</channel></rss>\n", encoding="utf-8")

    apply_base_path()

    n = sum(1 for _ in OUT.rglob("*.html"))
    print(f"Built {n} HTML pages ({len(posts)} posts, {len(services)} service pages) into {OUT}"
          + (f" with base path {BASE_PATH}" if BASE_PATH else ""))

    if "--serve" in sys.argv:
        import http.server, functools
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Serving on http://localhost:8000")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
