# Data Sources

Research Radar Hub only collects public metadata and public page text snippets.

## arXiv

Uses the public arXiv API through the `arxiv` Python package. The default delay is conservative and configurable in `config.yaml`.

## GitHub

Uses the public GitHub Search REST API. `GITHUB_PAT` is optional and only increases rate limits.

## NASA

NASA support is metadata-first:

- NASA STI/NTRS is enabled by default for public citation and technical report metadata.
- NASA TechPort is disabled by default because API access can require a token/session; set `TECHPORT_API_TOKEN` and enable `nasa.techport.enabled` when available.
- SAO/NASA ADS is disabled by default and requires `ADS_API_TOKEN`; it is treated as an optional literature metadata source.

The collectors store titles, abstracts/descriptions, links, keywords, dates, and PDF links when the source exposes them. They do not download PDFs during collection.

## Paper Understanding

The understanding pipeline extracts lightweight signals from metadata and optional public PDFs:

- formula candidates
- dataset and benchmark mentions
- code repository links
- metric mentions
- citation clues

PDF download is disabled by default. When enabled, it is bounded by file size, page count, timeout, and public URLs only. It does not run external code or install dependencies from papers.

## Courses

Course radar is configured through official public pages:

- MIT OpenCourseWare public pages.
- ETH Zurich Course Catalogue pages.
- Cambridge official course pages when accessible from the runtime environment.

The collector stores titles, links, summaries, and metadata. It does not download course materials, PDFs, videos, or files.

## Hacker News

Uses public endpoints for story metadata.

## CVE Feeds

Uses public vulnerability metadata sources such as NVD and CISA KEV.

## Website Changes

Configured pages are fetched at low frequency with robots.txt checks. Rendered JavaScript pages are intentionally skipped unless explicitly supported in a future release.
