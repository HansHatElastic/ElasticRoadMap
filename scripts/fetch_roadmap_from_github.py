#!/usr/bin/env python3
"""
Fetch all items from the Elastic Public Roadmap. Two modes:

1. **API (default)** – Fetches every issue from the elastic/roadmap repo via
   GitHub REST API (no auth). This collects the full set of roadmap items.

2. **Browser** – Use --browser to load the project board and scrape visible cards
   (requires Playwright; may show fewer items if the view is filtered).

Usage:
  python scripts/fetch_roadmap_from_github.py [--output PATH] [--browser]

Output: TSV that generate_roadmap_doc.py can use.
"""

import argparse
import csv
import os
import sys

ROADMAP_URL = "https://github.com/orgs/elastic/projects/2066/views/2"
ROADMAP_REPO_API = "https://api.github.com/repos/elastic/roadmap/issues"


def fetch_all_via_api() -> list:
    """Fetch all issues from elastic/roadmap via REST API (no auth)."""
    try:
        import requests
    except ImportError:
        return []
    rows = []
    page = 1
    per_page = 100
    while True:
        r = requests.get(
            ROADMAP_REPO_API,
            params={"state": "all", "per_page": per_page, "page": page},
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=30,
        )
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        for issue in data:
            title = (issue.get("title") or "").strip()
            if not title:
                continue
            url = issue.get("html_url") or ""
            state = (issue.get("state") or "").strip().capitalize()
            body = (issue.get("body") or "").strip()
            if len(body) > 400:
                body = body[:397] + "..."
            rows.append({
                "Title": title,
                "Status": state,
                "Link": url,
                "Description": body,
                "Assignees": "",
                "Labels": "",
            })
        if len(data) < per_page:
            break
        page += 1
    return rows


def run_browser_fetch(output_path: str) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is required. Run: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 1

    rows = []
    with sync_playwright() as p:
        # Prefer system Chrome to avoid Playwright browser path issues
        try:
            browser = p.chromium.launch(headless=True, channel="chrome")
        except Exception:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            page.goto(ROADMAP_URL, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"Navigation failed: {e}", file=sys.stderr)
            browser.close()
            return 1

        # Wait for project content: board has columns or cards
        page.wait_for_timeout(3000)

        # Scroll the main content area to load any lazy-loaded cards
        for _ in range(5):
            page.evaluate(
                """() => {
                const el = document.querySelector('[data-view-component="true"]') || document.querySelector('main') || document.body;
                el.scrollTop = el.scrollHeight;
                }"""
            )
            page.wait_for_timeout(800)

        # GitHub new project board: cards are often in columns; links go to issues/pull
        # Selectors that tend to work: card containers, then links inside them
        link_selector = 'a[href*="/issues/"], a[href*="/pull/"]'
        seen_urls = set()
        seen_titles = set()

        # Get all issue/PR links in the page that belong to elastic org
        links = page.query_selector_all(link_selector)
        for link in links:
            href = link.get_attribute("href") or ""
            if "github.com" in href:
                full_url = href if href.startswith("http") else "https://github.com" + (href if href.startswith("/") else "/" + href)
            else:
                full_url = ("https://github.com" + href) if href.startswith("/") else href
            if "/orgs/elastic/" in full_url or "/elastic/" in full_url:
                if full_url in seen_urls:
                    continue
            # Skip nav/header/footer links - focus on project content
            try:
                text = (link.inner_text() or "").strip()
            except Exception:
                text = ""
            if not text or len(text) > 500:
                continue
            # Avoid duplicates by URL and by normalized title
            key = (full_url, text[:100])
            if full_url in seen_urls and text[:80] in seen_titles:
                continue
            seen_urls.add(full_url)
            seen_titles.add(text[:80])

            # Status/column detection: optional; generator will group by "No status" if missing
            status = "No status"

            rows.append({
                "Title": text,
                "Status": status,
                "Link": full_url,
                "Description": "",
                "Assignees": "",
                "Labels": "",
            })

        browser.close()

    if not rows:
        print("No items extracted with issue links. Page structure may have changed.", file=sys.stderr)
        return 1

    write_tsv(output_path, rows)
    print(f"Fetched {len(rows)} items from the roadmap (browser) and wrote {output_path}")
    return 0


def write_tsv(output_path: str, rows: list) -> None:
    """Write rows to TSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fieldnames = ["Title", "Status", "Link", "Description", "Assignees", "Labels"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch all Elastic Public Roadmap items and save as TSV."
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "roadmap_export.tsv"),
        help="Output TSV path",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use Playwright to scrape the project board (default: use GitHub API for full list)",
    )
    args = parser.parse_args()

    if args.browser:
        sys.exit(run_browser_fetch(args.output))

    # Default: fetch all issues from elastic/roadmap via API
    rows = fetch_all_via_api()
    if not rows:
        print("Could not fetch issues via API (check network or install requests).", file=sys.stderr)
        sys.exit(1)
    write_tsv(args.output, rows)
    print(f"Fetched {len(rows)} items from the roadmap (API) and wrote {args.output}")
    sys.exit(0)


if __name__ == "__main__":
    main()
