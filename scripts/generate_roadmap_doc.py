#!/usr/bin/env python3
"""
Generate a Markdown document from an exported Elastic Public Roadmap view (TSV/CSV).

Usage:
  python scripts/generate_roadmap_doc.py [--input PATH] [--output PATH]

If no paths are given, uses data/roadmap_export.tsv and docs/elastic-public-roadmap.md.
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime

ROADMAP_URL = "https://github.com/orgs/elastic/projects/2066/views/2"

# Column name variants (case-insensitive) for mapping export columns
COLUMN_ALIASES = {
    "title": ["title", "name", "item", "issue", "card"],
    "status": ["status", "state", "stage", "column"],
    "link": ["link", "url", "html url", "issue url", "url link"],
    "description": ["description", "body", "summary", "content", "notes"],
}


def normalize_header(name):
    return (name or "").strip().lower()


def detect_delimiter(path):
    """Return delimiter: tab for .tsv, comma for .csv."""
    ext = os.path.splitext(path)[1].lower()
    return "\t" if ext == ".tsv" else ","


def find_column_index(headers, aliases):
    """Return index of first header that matches any alias, or None."""
    normalized = [normalize_header(h) for h in headers]
    for alias in aliases:
        for i, h in enumerate(normalized):
            if alias in h or h in alias:
                return i
    return None


def map_columns(headers):
    """Return dict: key -> column index (0-based)."""
    result = {}
    for key, aliases in COLUMN_ALIASES.items():
        idx = find_column_index(headers, aliases)
        if idx is not None:
            result[key] = idx
    return result


def read_rows(path):
    """Read TSV or CSV; return (list of dicts with title/status/link/description, raw headers)."""
    delim = detect_delimiter(path)
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter=delim)
        headers = next(reader, None)
        if not headers:
            return [], []
        col_map = map_columns(headers)
        if "title" not in col_map:
            raise ValueError(
                f"No 'title' column found. Headers: {headers}. "
                "Use a GitHub export that includes a title column."
            )
        rows = []
        for row in reader:
            if len(row) <= max(col_map.values(), default=0):
                continue
            item = {}
            for key, idx in col_map.items():
                if idx < len(row):
                    item[key] = (row[idx] or "").strip()
            if item.get("title"):
                rows.append(item)
        return rows, headers


def group_by_status(rows):
    """Group items by status; use 'No status' if missing."""
    groups = defaultdict(list)
    for r in rows:
        status = (r.get("status") or "No status").strip() or "No status"
        groups[status].append(r)
    return dict(groups)


def escape_md_link(text):
    """Escape markdown link text (brackets)."""
    if not text:
        return ""
    return text.replace("[", "\\[").replace("]", "\\]")


def write_markdown(rows, output_path, run_date=None):
    """Write the full roadmap Markdown document."""
    run_date = run_date or datetime.utcnow().strftime("%Y-%m-%d")
    groups = group_by_status(rows)

    lines = [
        "# Elastic Public Roadmap – Overview",
        "",
        "This document is a snapshot of the [Elastic Public Roadmap]({url}) for technical teams who already work with the Elastic stack. It summarises what’s on the board so you can share or discuss priorities with your colleagues. For the latest updates and live view, use the source link below.",
        "",
        f"**Source:** [Elastic Public Roadmap (GitHub)]({ROADMAP_URL})",
        "",
        "---",
        "",
        "## How this roadmap is organised",
        "",
        "Items are grouped by status (e.g. In progress, Planned, Done). Each entry lists the title and, when available, a link to the source issue or card.",
        "",
        "---",
        "",
    ]

    # Order sections: common status order first, then alphabetically for the rest
    status_order = ["In progress", "In Progress", "Planned", "Backlog", "Open", "Done", "Completed", "Closed", "No status"]
    ordered_statuses = [s for s in status_order if s in groups]
    for k in sorted(groups.keys(), key=str.lower):
        if k not in ordered_statuses:
            ordered_statuses.append(k)

    for status in ordered_statuses:
        items = groups[status]
        lines.append(f"## {status}")
        lines.append("")
        for r in items:
            title = escape_md_link(r.get("title", ""))
            link = (r.get("link") or "").strip()
            desc = (r.get("description") or "").strip()
            if link and title:
                lines.append(f"- **[{title}]({link})**")
            elif title:
                lines.append(f"- **{title}**")
            if desc:
                lines.append(f"  - {desc}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "For the current list and any changes since this snapshot, see the live board: [Elastic Public Roadmap]({url}).",
        "",
        f"*Last updated: {run_date} (from exported view data).*",
        "",
    ])

    content = "\n".join(lines).format(url=ROADMAP_URL)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Elastic Public Roadmap Markdown from an exported TSV/CSV view."
    )
    parser.add_argument(
        "--input", "-i",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "roadmap_export.tsv"),
        help="Path to exported view file (TSV or CSV)",
    )
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "elastic-public-roadmap.md"),
        help="Path to output Markdown file",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(
            f"Input file not found: {args.input}",
            file=sys.stderr,
        )
        print(
            "Export the roadmap view from GitHub (view menu → Export view data), "
            "save as TSV or CSV, and pass it with --input.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        rows, _ = read_rows(args.input)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    write_markdown(rows, args.output)
    print(f"Wrote {len(rows)} items to {args.output}")


if __name__ == "__main__":
    main()
