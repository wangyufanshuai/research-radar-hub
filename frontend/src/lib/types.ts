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

export interface PaperUnderstanding {
  id: number;
  paper_id?: number | null;
  source: string;
  source_id: string;
  title: string;
  url?: string | null;
  pdf_url?: string | null;
  text_excerpt?: string | null;
  formula_candidates?: string | null;
  dataset_mentions?: string | null;
  code_mentions?: string | null;
  citation_mentions?: string | null;
  metric_mentions?: string | null;
  understanding_status: string;
  error_message?: string | null;
  analyzed_at: string;
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

export type CollectSource = "arxiv" | "github" | "hn" | "course" | "nasa" | "all";

export interface CollectResponse {
  source: string;
  status: string;
  records_fetched: number;
  records_new: number;
  records_updated: number;
  duration_secs: number;
  error?: string | null;
}

// ---- AI Scientist ----

export interface ScientistTask {
  id: number;
  topic: string;
  status: string;
  query?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScientistTaskItem {
  id: number;
  task_id: number;
  source: "arxiv" | "github" | string;
  source_id: string;
  title: string;
  url?: string | null;
  summary?: string | null;
  relevance_score: number;
  novelty_score: number;
  reproducibility_score: number;
  selected: boolean;
  understanding?: PaperUnderstanding | null;
}

export interface ScientistRun {
  id: number;
  task_id: number;
  stage: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  message?: string | null;
  error_message?: string | null;
}

export interface ScientistArtifact {
  id: number;
  task_id: number;
  kind: string;
  title: string;
  body_markdown: string;
  html_path?: string | null;
  created_at_artifact: string;
}

export interface ScientistTaskDetail extends ScientistTask {
  items: ScientistTaskItem[];
  artifacts: ScientistArtifact[];
  runs: ScientistRun[];
}

export interface ScientistTaskList {
  items: ScientistTask[];
  total: number;
  offset: number;
  limit: number;
}
