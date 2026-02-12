# Elastic Public Roadmap – Doc Generator

This project helps you turn the [Elastic Public Roadmap](https://github.com/orgs/elastic/projects/2066/views/2) (GitHub project 2066, view 2) into a single Markdown document suitable for sharing with technical audiences and for importing into Google Docs.

## Requirements

- Python 3.x (use the latest available on your system: system `python3`, [pyenv](https://github.com/pyenv/pyenv), or Homebrew).

## Setup

1. **Create and activate a virtual environment** (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Fetch the full roadmap (recommended)**

   To collect **all** roadmap items, run the fetcher. It uses the GitHub API by default (no login required):

   ```bash
   python scripts/fetch_roadmap_from_github.py
   ```

   This fetches every issue from the [elastic/roadmap](https://github.com/elastic/roadmap) repo and writes `data/roadmap_export.tsv`. Then run the generator (see below).

   **Optional:** To scrape the project board view instead (fewer items, requires Playwright): `python scripts/fetch_roadmap_from_github.py --browser`. You may need `playwright install chromium` or system Chrome.

   **Alternative:** Export the view manually from the [Elastic Public Roadmap](https://github.com/orgs/elastic/projects/2066/views/2) (view menu → **Export view data**), save as `data/roadmap_export.tsv`, then run the generator.

## Generate the Markdown document

From the project root (with the venv activated if you use it):

```bash
python scripts/generate_roadmap_doc.py
```

This reads `data/roadmap_export.tsv` and writes `docs/elastic-public-roadmap.md`.

**Custom paths:**

```bash
python scripts/generate_roadmap_doc.py --input path/to/export.tsv --output path/to/roadmap.md
```



## Files

| Path | Purpose |
|------|--------|
| `.venv/` | Virtual environment (create with `python3 -m venv .venv`). |
| `scripts/generate_roadmap_doc.py` | Reads an exported TSV/CSV and writes the Markdown doc. |
| `data/roadmap_export.tsv` | Sample export; replace with your own export from the roadmap view. |
| `docs/elastic-public-roadmap.md` | Generated roadmap document. |
| `README.md` | This file. |

