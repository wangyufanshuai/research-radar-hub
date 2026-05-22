# Data Sources

Research Radar Hub only collects public metadata and public page text snippets.

## arXiv

Uses the public arXiv API through the `arxiv` Python package. The default delay is conservative and configurable in `config.yaml`.

## GitHub

Uses the public GitHub Search REST API. `GITHUB_PAT` is optional and only increases rate limits.

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
