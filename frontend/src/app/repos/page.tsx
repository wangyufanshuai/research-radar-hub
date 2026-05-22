"use client";

import { useEffect, useState, useCallback } from "react";
import { fetchRepos } from "@/lib/api";
import type { Repo, ReposResponse } from "@/lib/types";

const POPULAR_LANGUAGES = [
  "",
  "JavaScript",
  "TypeScript",
  "Python",
  "Java",
  "Go",
  "Rust",
  "C++",
  "C",
  "Ruby",
  "Swift",
  "Kotlin",
  "PHP",
  "Shell",
];

const STAR_OPTIONS = [
  { label: "Any stars", value: 0 },
  { label: "10+ stars", value: 10 },
  { label: "50+ stars", value: 50 },
  { label: "100+ stars", value: 100 },
  { label: "500+ stars", value: 500 },
  { label: "1000+ stars", value: 1000 },
  { label: "5000+ stars", value: 5000 },
  { label: "10000+ stars", value: 10000 },
];

export default function ReposPage() {
  const [data, setData] = useState<ReposResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [language, setLanguage] = useState("");
  const [minStars, setMinStars] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadRepos = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchRepos({ language, min_stars: minStars, offset, limit });
      setData(result);
    } catch (err) {
      console.error("Failed to fetch repos:", err);
    } finally {
      setLoading(false);
    }
  }, [language, minStars, offset]);

  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  function handleLanguageChange(value: string) {
    setLanguage(value);
    setOffset(0);
  }

  function handleMinStarsChange(value: string) {
    setMinStars(Number(value));
    setOffset(0);
  }

  function handlePrev() {
    setOffset((prev) => Math.max(0, prev - limit));
  }

  function handleNext() {
    if (data && offset + limit < data.total) {
      setOffset((prev) => prev + limit);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Repositories</h1>
        <p className="mt-1 text-sm text-gray-500">
          Popular repositories collected from GitHub
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col gap-4 sm:flex-row">
          <select
            value={language}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className="input-field sm:w-48"
          >
            <option value="">All Languages</option>
            {POPULAR_LANGUAGES.filter(Boolean).map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
          <select
            value={minStars}
            onChange={(e) => handleMinStarsChange(e.target.value)}
            className="input-field sm:w-48"
          >
            {STAR_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="space-y-3">
                <div className="h-5 w-1/2 rounded bg-gray-200" />
                <div className="h-3 w-full rounded bg-gray-200" />
                <div className="h-3 w-1/3 rounded bg-gray-200" />
              </div>
            </div>
          ))}
        </div>
      ) : data && data.repos.length > 0 ? (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Showing {offset + 1}-{Math.min(offset + limit, data.total)} of{" "}
              {data.total} repositories
            </p>
          </div>
          <div className="space-y-4">
            {data.repos.map((repo: Repo) => (
              <article key={repo.id} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <a
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-base font-semibold text-accent hover:text-accent-dark"
                      >
                        {repo.full_name}
                      </a>
                      {repo.language && (
                        <span className="badge-green">{repo.language}</span>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-gray-600">
                      {repo.description || "No description"}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <svg className="h-4 w-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        {repo.stars.toLocaleString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                        </svg>
                        {repo.forks.toLocaleString()}
                      </span>
                      {repo.open_issues > 0 && (
                        <span className="flex items-center gap-1">
                          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          {repo.open_issues}
                        </span>
                      )}
                      <span>Updated {new Date(repo.updated_at).toLocaleDateString()}</span>
                    </div>
                    {repo.topics && repo.topics.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {repo.topics.slice(0, 5).map((topic) => (
                          <span key={topic} className="badge-blue">
                            {topic}
                          </span>
                        ))}
                        {repo.topics.length > 5 && (
                          <span className="badge bg-gray-100 text-gray-600">
                            +{repo.topics.length - 5} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <button
              onClick={handlePrev}
              disabled={offset === 0}
              className="btn-secondary disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">
              Page {Math.floor(offset / limit) + 1} of{" "}
              {Math.ceil(data.total / limit)}
            </span>
            <button
              onClick={handleNext}
              disabled={offset + limit >= data.total}
              className="btn-secondary disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <div className="card flex h-40 items-center justify-center">
          <p className="text-gray-500">No repositories found</p>
        </div>
      )}
    </div>
  );
}
