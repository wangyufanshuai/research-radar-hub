from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CollectorRateLimit(BaseModel):
    request_delay_seconds: float = 3.0
    max_concurrent: int = 1
    burst_limit: int = 5
    burst_window_seconds: int = 60


class CollectorRetry(BaseModel):
    max_retries: int = 3
    backoff_factor: float = 2.0
    backoff_max_seconds: float = 60.0
    retryable_status_codes: list[int] = [429, 500, 502, 503, 504]


class ComplianceConfig(BaseModel):
    user_agent: str = (
        "OpenDataHub/1.0 (public low-frequency research monitor; "
        "contact configurable)"
    )
    respect_robots_txt: bool = True
    max_body_bytes: int = 1_048_576


class CacheConfig(BaseModel):
    enabled: bool = True
    directory: str = "cache"
    default_ttl_seconds: int = 3600


class ArxivSourceConfig(BaseModel):
    enabled: bool = True
    default_categories: list[str] = ["cs.AI", "hep-ph"]
    max_results_per_query: int = 100
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=3.0)
    retry: CollectorRetry = CollectorRetry()
    robots_required: bool = False


class GitHubSourceConfig(BaseModel):
    enabled: bool = True
    default_languages: list[str] = ["Python", "TypeScript", "Rust"]
    min_stars: int = 50
    max_results_per_query: int = 100
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=1.0)
    retry: CollectorRetry = CollectorRetry()
    robots_required: bool = False


class HNSourceConfig(BaseModel):
    enabled: bool = True
    story_types: list[str] = ["top", "best", "new"]
    max_stories_per_fetch: int = 100
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=0.5)
    retry: CollectorRetry = CollectorRetry()
    robots_required: bool = False


class SchoolNoticeSource(BaseModel):
    id: str
    name: str
    url: str
    selector: str | None = "a"
    keywords: list[str] = []
    robots_required: bool = True


class SchoolNoticesConfig(BaseModel):
    enabled: bool = True
    sources: list[SchoolNoticeSource] = []
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=3.0)
    retry: CollectorRetry = CollectorRetry()
    robots_required: bool = True


class WebsitePageConfig(BaseModel):
    name: str
    url: str
    selector: str | None = "body"
    render: bool = False
    enabled: bool = True
    check_interval_minutes: int = 360
    robots_required: bool = True


class WebsiteChangesConfig(BaseModel):
    enabled: bool = True
    pages: list[WebsitePageConfig] = []
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=3.0)
    retry: CollectorRetry = CollectorRetry()
    robots_required: bool = True


class CVEConfig(BaseModel):
    enabled: bool = True
    sources: list[str] = ["nvd", "cisa_kev"]
    severity_min: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    days_back: int = 2
    max_results_per_query: int = 100
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=6.0)
    retry: CollectorRetry = CollectorRetry(max_retries=2)
    robots_required: bool = False


class ResearchTopicConfig(BaseModel):
    name: str
    categories: list[str] = []
    keywords: list[str] = []


class ResearchRadarConfig(BaseModel):
    enabled: bool = True
    topics: dict[str, ResearchTopicConfig] = {}
    lookback_days: int = 1
    max_items_per_topic_source: int = 5
    min_score: float = 1.0
    llm_max_items_per_report: int = 2
    output_directory: str = "reports/research_radar"


class CourseSourceConfig(BaseModel):
    id: str
    institution: str
    url: str
    kind: Literal["rss", "html"] = "html"
    selector: str | None = "a"
    keywords: list[str] = []
    department: str | None = None
    level: str | None = None
    robots_required: bool = True
    enabled: bool = True


class CourseRadarConfig(BaseModel):
    enabled: bool = True
    sources: list[CourseSourceConfig] = []
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=3.0)
    retry: CollectorRetry = CollectorRetry()
    robots_required: bool = True


class NasaEndpointConfig(BaseModel):
    enabled: bool = True
    base_url: str
    max_results_per_query: int = 20


class NasaConfig(BaseModel):
    enabled: bool = True
    ntrs: NasaEndpointConfig = NasaEndpointConfig(
        base_url="https://ntrs.nasa.gov/api/citations/search"
    )
    techport: NasaEndpointConfig = NasaEndpointConfig(
        enabled=False,
        base_url="https://techport.nasa.gov/api/projects/search"
    )
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=3.0)
    retry: CollectorRetry = CollectorRetry(max_retries=2)
    robots_required: bool = False


class AdsConfig(BaseModel):
    enabled: bool = False
    base_url: str = "https://api.adsabs.harvard.edu/v1/search/query"
    max_results_per_query: int = 20
    rate_limit: CollectorRateLimit = CollectorRateLimit(request_delay_seconds=3.0)
    retry: CollectorRetry = CollectorRetry(max_retries=2)
    robots_required: bool = False


class PaperUnderstandingConfig(BaseModel):
    enabled: bool = True
    download_pdfs: bool = False
    max_pdf_bytes: int = 5_000_000
    max_pdf_pages: int = 5
    timeout_seconds: int = 20
    text_excerpt_chars: int = 6_000


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///data/open_data_hub.db"
    echo: bool = False


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]


class AppConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    cache: CacheConfig = CacheConfig()
    compliance: ComplianceConfig = ComplianceConfig()
    arxiv: ArxivSourceConfig = ArxivSourceConfig()
    github: GitHubSourceConfig = GitHubSourceConfig()
    hackernews: HNSourceConfig = HNSourceConfig()
    school_notices: SchoolNoticesConfig = SchoolNoticesConfig()
    website_changes: WebsiteChangesConfig = WebsiteChangesConfig()
    cve: CVEConfig = CVEConfig()
    research_radar: ResearchRadarConfig = ResearchRadarConfig()
    course_radar: CourseRadarConfig = CourseRadarConfig()
    nasa: NasaConfig = NasaConfig()
    ads: AdsConfig = AdsConfig()
    paper_understanding: PaperUnderstandingConfig = PaperUnderstandingConfig()


class Secrets(BaseSettings):
    github_pat: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    ads_api_token: str = ""
    techport_api_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


_config: AppConfig | None = None
_secrets: Secrets | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        import yaml

        config_path = _PROJECT_ROOT / "config.yaml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            _config = AppConfig(**raw)
        else:
            _config = AppConfig()
    return _config


def get_secrets() -> Secrets:
    global _secrets
    if _secrets is None:
        _secrets = Secrets()
    return _secrets


def get_project_root() -> Path:
    return _PROJECT_ROOT
