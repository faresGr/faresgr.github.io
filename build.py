"""Builds the site into _site/. Usage: python build.py [--serve]

Content: site.yml (home page), _posts/*.md (blog), assets/ (copied as is).
Templates: templates/*.html (Jinja2). Styles: assets/style.css.
"""
import datetime as dt
import html
import re
import shutil
import sys
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
SLUG_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")


def md(text):
    return markdown.markdown(text or "", extensions=["tables", "fenced_code", "footnotes", "attr_list", "smarty"])


def md_inline(text):
    return re.sub(r"^<p>(.*)</p>$", r"\1", md(text).strip(), flags=re.S)


def read_post(path):
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front) or {}
    y, m, d, slug = SLUG_DATE.match(path.name).groups()
    date = meta.get("date")
    if isinstance(date, str):
        date = dt.datetime.fromisoformat(date.replace(" ", "T"))
    if not isinstance(date, dt.datetime):
        date = dt.datetime(int(y), int(m), int(d), tzinfo=dt.timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=dt.timezone.utc)
    url = meta.get("permalink") or f"/blog/{y}/{slug}/"
    words = len(re.findall(r"\w+", body))
    return {**meta, "date": date, "url": url, "content": md(body),
            "minutes": max(1, round(words / 230)), "draft": meta.get("draft", False)}


def write(url, text):
    target = OUT / url.lstrip("/")
    if url.endswith("/"):
        target = target / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build():
    site = yaml.safe_load((ROOT / "site.yml").read_text(encoding="utf-8"))
    now = dt.datetime.now(dt.timezone.utc)
    posts = [read_post(p) for p in sorted((ROOT / "_posts").glob("*.md"))]
    posts = sorted((p for p in posts if not p["draft"] and p["date"] <= now), key=lambda p: p["date"], reverse=True)

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    env.filters.update(md=md, md_inline=md_inline, abs=lambda u: u if "://" in u else site["url"] + "/" + u.lstrip("/"),
                       rel=lambda u: u if (":" in u or u.startswith("/")) else "/" + u,
                       month=lambda s: dt.datetime.strptime(str(s), "%Y-%m").strftime("%b %Y"))
    import hashlib
    css_version = hashlib.sha256((ROOT / "assets" / "style.css").read_bytes()).hexdigest()[:10]
    common = {"site": site, "year": now.year, "css_version": css_version}

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").touch()

    write("/", env.get_template("home.html").render(**common, posts=posts, page={"url": "/"}))
    write("/blog/", env.get_template("blog.html").render(**common, posts=posts, page={"url": "/blog/", "title": "Writing"}))
    for post in posts:
        write(post["url"], env.get_template("post.html").render(**common, page=post))
    # Old al-folio address, still linked from the CV.
    write("/publications/", '<!doctype html><meta charset="utf-8"><title>Research</title>'
          '<meta http-equiv="refresh" content="0; url=/#research"><link rel="canonical" href="/#research">'
          '<a href="/#research">Research</a>')
    write("/404.html", env.get_template("404.html").render(**common, page={"url": "/404.html", "title": "Not found"}))

    items = "".join(
        f"<item><title>{html.escape(p['title'])}</title><link>{site['url']}{p['url']}</link>"
        f"<guid>{site['url']}{p['url']}</guid><pubDate>{format_datetime(p['date'])}</pubDate>"
        f"<description>{html.escape(p.get('description', ''))}</description></item>" for p in posts)
    write("/feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
          f"<title>{html.escape(site['name'])}</title><link>{site['url']}</link>"
          f"<description>{html.escape(site['description'])}</description>{items}</channel></rss>")
    urls = ["/", "/blog/"] + [p["url"] for p in posts]
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{site['url']}{u}</loc></url>" for u in urls) + "</urlset>")
    write("/robots.txt", f"User-agent: *\nDisallow:\n\nSitemap: {site['url']}/sitemap.xml\n")
    print(f"Built {len(posts)} post(s) into {OUT}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Serving on http://localhost:8000")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()
