from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def content_hash(*parts: str | None) -> str:
    raw = "\n".join(normalize_text(part) for part in parts if part is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def absolute_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("javascript:", "mailto:", "tel:")):
        return None
    return urljoin(base_url, href)


def extract_selected_text(html: str, selector: str | None) -> tuple[str | None, str]:
    soup = parse_html(html)
    title = normalize_text(soup.title.get_text(" ")) if soup.title else None
    node = soup.select_one(selector) if selector else soup.body
    text = normalize_text(node.get_text(" ")) if node else normalize_text(soup.get_text(" "))
    return title, text
