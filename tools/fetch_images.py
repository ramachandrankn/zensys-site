#!/usr/bin/env python3
"""Copy every image the site still loads from the old WordPress server into
static/img/wp/, so nothing breaks once zensys.in points to GitHub Pages.

Run ONCE, from any computer with internet, BEFORE switching DNS:
    python3 tools/fetch_images.py
    python3 build.py         # pages now use the local copies
    git add -A && git commit -m "Bring images in-house" && git push
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "static" / "img" / "wp"
DEST.mkdir(parents=True, exist_ok=True)
pat = re.compile(r"https?://(?:www\.)?zensys\.in/(?:wp-content/uploads|resources/img)/[^\s)\"'>]+")
urls = set()
for f in list((ROOT / "content").rglob("*.md")) + list((ROOT / "content").rglob("*.yml")):
    urls.update(pat.findall(f.read_text(encoding="utf-8")))
ok = fail = 0
for u in sorted(urls):
    name = re.sub(r"^https?://(?:www\.)?zensys\.in/(?:wp-content/uploads|resources/img)/", "", u).replace("/", "_")
    out = DEST / name
    if out.exists():
        continue
    # curl is used because the old site's firewall rejects Python's own HTTP client
    r = subprocess.run(["curl", "-sS", "-f", "-m", "60", "-A", "Mozilla/5.0", "-o", str(out), "-w", "%{content_type}", u],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.startswith("image/"):
        ok += 1
        print("saved", name)
    else:
        out.unlink(missing_ok=True)
        fail += 1
        print("FAILED", u, r.stdout or r.stderr.strip())
print(f"done: {ok} downloaded, {fail} failed, {len(urls)} referenced")
