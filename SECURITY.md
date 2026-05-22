# Security Policy

## Supported Versions

The `main` branch is the only supported development line before the first tagged release.

## Reporting a Vulnerability

Please open a private security advisory if the repository is hosted on GitHub. If advisories are not available, contact the maintainer directly and avoid posting exploit details in a public issue.

## Secret Handling

- Never commit `.env` files or API keys.
- Use `GITHUB_PAT`, `OPENAI_API_KEY`, and SMTP credentials only through environment variables.
- Generated SQLite databases, cache files, and reports are local runtime artifacts and are ignored by git.

## Data Collection Safety

Research Radar Hub is designed for public metadata collection. It should not be used to bypass authentication, paywalls, CAPTCHA, robots.txt restrictions, or access controls.
