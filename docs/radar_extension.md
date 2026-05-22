# 合规公开数据采集雷达

## 项目目录

本扩展基于现有 `open-data-hub`：

```text
backend/collectors/        # arXiv, GitHub, 学校公告, 网站变更, CVE 采集器
backend/models/            # SQLite/SQLAlchemy 表模型
backend/repositories/      # 查询与 upsert
backend/api/               # FastAPI 路由
backend/scripts/           # CLI 采集与日报生成
config.yaml                # 数据源、限速、合规配置
tests/                     # 单元和 API 测试
```

## 依赖

新增依赖写入 `backend/requirements.txt`：

```text
beautifulsoup4
lxml
feedparser
python-dateutil
markdown
```

保留现有 `FastAPI`、`SQLAlchemy`、`SQLite`、`httpx`、`arxiv`、`PyGithub`、`pandas`、`pytest`。

## 数据库表

新增表：

- `notices`: 学校公告公开元数据。
- `watched_pages`: 网站变更监控目标。
- `page_snapshots`: 变更快照和简短 diff。
- `cve_items`: NVD/CISA KEV 漏洞元数据。
- `daily_reports`: Markdown 日报。

`papers`、`repos`、`stories`、`fetch_logs` 继续复用。

## 运行命令

```powershell
cd E:\xuexi\open-data-hub
backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

python -m backend.scripts.collect --source all --incremental
python -m backend.scripts.collect --source school
python -m backend.scripts.collect --source website
python -m backend.scripts.collect --source cve
python -m backend.scripts.daily_report --kind all

uvicorn backend.main:app --reload --port 8000
```

API：

```text
POST /api/v1/collect/{source}
GET  /api/v1/radar/notices
GET  /api/v1/radar/changes
GET  /api/v1/radar/cves
GET  /api/v1/reports/daily?date=YYYY-MM-DD
```

## 配置

`config.yaml` 新增：

- `compliance`: User-Agent、robots.txt、最大响应体。
- `school_notices`: 学校公告公开页面配置。
- `website_changes`: 网站正文变更监控配置。
- `cve`: NVD/CISA KEV 元数据配置。

学校和网站监控默认 `sources/pages: []`，避免占位配置误请求外部站点。添加真实公开页面前，应先确认页面允许公开低频访问。

## 测试

```powershell
pytest tests -q
```

已覆盖：

- HTML selector 提取和 hash。
- 学校公告关键词过滤。
- 网站变更 hash/diff。
- CVE JSON 映射。
- 新增雷达 API 和日报 API。

## 合规说明

- 只采集公开网页、官方 API、RSS/JSON 元数据。
- 不登录，不绕过验证码、风控、签名、付费墙或访问控制。
- 不采集隐私数据，不下载论文 PDF、附件、音视频或其他受版权保护文件。
- 默认低频串行，带缓存、重试、robots.txt 检查和明确 User-Agent。
- 遇到 `401/403/429` 会停止本源本轮采集并记录失败。

## 后续扩展

- 为学校公告补具体公开栏目配置。
- 增加通知渠道，如邮件、Slack、企业微信。
- 增加 Streamlit 本地看板。
- 对明确允许且必须渲染的公开页面，再加入 Playwright。
