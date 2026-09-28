# faresgr.github.io

My personal site: a home page, a blog and a list of publications, built by one small Python script.

## Edit

- **Home page** (bio, links, news, publications): `site.yml`
- **Blog posts**: add `_posts/YYYY-MM-DD-slug.md` with front matter (`title`, `description`, optional `permalink`, `og_image`, `draft: true`). The URL defaults to `/blog/YYYY/slug/`.
- **Look**: `templates/*.html` (Jinja2) and `assets/style.css`
- **Files** (images, PDFs): `assets/`, copied as is

## Preview locally

```bash
pip install -r requirements.txt
python build.py --serve   # http://localhost:8000
```

## Publish

Push to `master`. GitHub Actions runs `build.py` and deploys `_site/` to the `gh-pages` branch.
