from enum import Enum


class DataSource(str, Enum):
    ARXIV = "arxiv"
    GITHUB = "github"
    HACKERNEWS = "hn"


class FetchStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
