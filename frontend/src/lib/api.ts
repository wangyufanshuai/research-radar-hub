import type {
  PapersResponse,
  PapersQuery,
  ReposResponse,
  ReposQuery,
  StoriesResponse,
  StoriesQuery,
  DashboardStats,
  TrendingResponse,
  CollectSource,
  CollectResponse,
  DailyReport,
  PaperUnderstanding,
  ScientistTask,
  ScientistTaskDetail,
  ScientistTaskList,
} from "./types";

const API_BASE = "/api/v1";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiGet<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(endpoint, window.location.origin);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

async function apiPost<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }
  const response = await fetch(url.toString(), { method: "POST" });

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

function parseJsonList(value?: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return value.split(",").map((item) => item.trim()).filter(Boolean);
  }
}

// ---- Papers API ----

export async function fetchPapers(query: PapersQuery = {}): Promise<PapersResponse> {
  const data = await apiGet<any>(`${API_BASE}/papers`, {
    keyword: query.keyword,
    category: query.category,
    offset: query.offset ?? 0,
    limit: query.limit ?? 20,
  });
  return {
    papers: data.items.map((item: any) => ({
      id: item.id,
      title: item.title,
      authors: parseJsonList(item.authors),
      abstract: item.abstract ?? "",
      category: item.primary_category ?? "",
      arxiv_id: item.arxiv_id,
      published_date: item.published,
      url: item.entry_url ?? item.pdf_url ?? "",
    })),
    total: data.total,
    offset: data.offset,
    limit: data.limit,
  };
}

export async function analyzePaperUnderstanding(paperId: number, allowPdf = false): Promise<PaperUnderstanding> {
  return apiPost<PaperUnderstanding>(`/papers/${paperId}/understanding`, { allow_pdf: allowPdf });
}

// ---- Repos API ----

export async function fetchRepos(query: ReposQuery = {}): Promise<ReposResponse> {
  const data = await apiGet<any>(`${API_BASE}/repos`, {
    language: query.language,
    min_stars: query.min_stars,
    offset: query.offset ?? 0,
    limit: query.limit ?? 20,
  });
  return {
    repos: data.items.map((item: any) => ({
      id: item.id,
      full_name: item.full_name,
      description: item.description ?? "",
      language: item.language ?? "",
      stars: item.stars ?? 0,
      forks: item.forks ?? 0,
      open_issues: item.open_issues ?? 0,
      url: item.html_url ?? "",
      topics: parseJsonList(item.topics),
      updated_at: item.pushed_at_gh ?? new Date().toISOString(),
    })),
    total: data.total,
    offset: data.offset,
    limit: data.limit,
  };
}

// ---- Stories API ----

export async function fetchStories(query: StoriesQuery = {}): Promise<StoriesResponse> {
  const data = await apiGet<any>(`${API_BASE}/stories`, {
    min_score: query.min_score,
    offset: query.offset ?? 0,
    limit: query.limit ?? 20,
  });
  return {
    stories: data.items.map((item: any) => ({
      id: item.id,
      title: item.title,
      url: item.url ?? "",
      score: item.score ?? 0,
      author: item.author ?? "",
      descendants: item.descendants ?? 0,
      hn_id: item.hn_id,
      posted_at: item.time_published,
    })),
    total: data.total,
    offset: data.offset,
    limit: data.limit,
  };
}

// ---- Analysis API ----

export async function fetchStats(): Promise<DashboardStats> {
  const data = await apiGet<any>(`${API_BASE}/analysis/stats`);
  return {
    papers_count: data.total_papers ?? 0,
    repos_count: data.total_repos ?? 0,
    stories_count: data.total_stories ?? 0,
    last_updated: new Date().toISOString(),
  };
}

export async function fetchTrending(days: number = 7): Promise<TrendingResponse> {
  const data = await apiGet<any>(`${API_BASE}/analysis/trending`, { days });
  return {
    topics: data.items.map((item: any) => ({
      topic: item.keyword,
      count: item.count,
      source: "all",
    })),
    period_days: data.period_days,
  };
}

// ---- Reports API ----

export async function fetchResearchReport(refresh = false): Promise<DailyReport> {
  return apiGet<DailyReport>(`${API_BASE}/reports/daily`, {
    kind: "research",
    refresh,
  });
}

// ---- Collect API ----

export async function triggerCollect(source: CollectSource): Promise<CollectResponse> {
  return apiPost<CollectResponse>(`/collect/${source}`, { incremental: true });
}

// ---- AI Scientist API ----

export async function createScientistTask(topic: string, use_llm = true): Promise<ScientistTask> {
  const response = await fetch(`${API_BASE}/scientist/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, max_papers: 20, max_repos: 10, use_llm }),
  });

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<ScientistTask>;
}

export async function runScientistTask(
  taskId: number,
  options: { max_papers?: number; max_repos?: number; use_llm?: boolean } = {},
): Promise<ScientistTaskDetail> {
  return apiPost<ScientistTaskDetail>(`/scientist/tasks/${taskId}/run`, {
    max_papers: options.max_papers ?? 20,
    max_repos: options.max_repos ?? 10,
    use_llm: options.use_llm ?? true,
  });
}

export async function fetchScientistTask(taskId: number): Promise<ScientistTaskDetail> {
  return apiGet<ScientistTaskDetail>(`${API_BASE}/scientist/tasks/${taskId}`);
}

export async function fetchScientistTasks(offset = 0, limit = 10): Promise<ScientistTaskList> {
  return apiGet<ScientistTaskList>(`${API_BASE}/scientist/tasks`, { offset, limit });
}
