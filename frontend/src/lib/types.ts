// ---- Paper (arXiv) ----

export interface Paper {
  id: number;
  title: string;
  authors: string[];
  abstract: string;
  category: string;
  arxiv_id: string;
  published_date: string;
  url: string;
}

export interface PapersResponse {
  papers: Paper[];
  total: number;
  offset: number;
  limit: number;
}

export interface PapersQuery {
  keyword?: string;
  category?: string;
  offset?: number;
  limit?: number;
}

// ---- Repo (GitHub) ----

export interface Repo {
  id: number;
  full_name: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  open_issues: number;
  url: string;
  topics: string[];
  updated_at: string;
}

export interface ReposResponse {
  repos: Repo[];
  total: number;
  offset: number;
  limit: number;
}

export interface ReposQuery {
  language?: string;
  min_stars?: number;
  offset?: number;
  limit?: number;
}

// ---- Story (Hacker News) ----

export interface Story {
  id: number;
  title: string;
  url: string;
  score: number;
  author: string;
  descendants: number;
  hn_id: number;
  posted_at: string;
}

export interface StoriesResponse {
  stories: Story[];
  total: number;
  offset: number;
  limit: number;
}

export interface StoriesQuery {
  min_score?: number;
  offset?: number;
  limit?: number;
}

// ---- Analysis ----

export interface DashboardStats {
  papers_count: number;
  repos_count: number;
  stories_count: number;
  last_updated: string;
}

export interface TrendingTopic {
  topic: string;
  count: number;
  source: string;
}

export interface TrendingResponse {
  topics: TrendingTopic[];
  period_days: number;
}

// ---- Reports ----

export interface DailyReport {
  id: number;
  report_date: string;
  kind: string;
  title: string;
  body_markdown: string;
  created_at_report: string;
}

// ---- Collect ----

export type CollectSource = "arxiv" | "github" | "hn" | "course" | "all";

export interface CollectResponse {
  source: string;
  status: string;
  records_fetched: number;
  records_new: number;
  records_updated: number;
  duration_secs: number;
  error?: string | null;
}
