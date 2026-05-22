"use client";

import { useEffect, useState, useCallback } from "react";
import { fetchStories } from "@/lib/api";
import type { Story, StoriesResponse } from "@/lib/types";

const SCORE_OPTIONS = [
  { label: "Any score", value: 0 },
  { label: "10+ points", value: 10 },
  { label: "50+ points", value: 50 },
  { label: "100+ points", value: 100 },
  { label: "200+ points", value: 200 },
  { label: "500+ points", value: 500 },
  { label: "1000+ points", value: 1000 },
];

function getDomainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

export default function StoriesPage() {
  const [data, setData] = useState<StoriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadStories = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchStories({ min_score: minScore, offset, limit });
      setData(result);
    } catch (err) {
      console.error("Failed to fetch stories:", err);
    } finally {
      setLoading(false);
    }
  }, [minScore, offset]);

  useEffect(() => {
    loadStories();
  }, [loadStories]);

  function handleMinScoreChange(value: string) {
    setMinScore(Number(value));
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

  function scoreColor(score: number): string {
    if (score >= 500) return "text-orange-600 bg-orange-50";
    if (score >= 100) return "text-orange-500 bg-orange-50";
    return "text-gray-600 bg-gray-50";
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stories</h1>
        <p className="mt-1 text-sm text-gray-500">
          Top stories collected from Hacker News
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col gap-4 sm:flex-row">
          <select
            value={minScore}
            onChange={(e) => handleMinScoreChange(e.target.value)}
            className="input-field sm:w-48"
          >
            {SCORE_OPTIONS.map((opt) => (
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
              <div className="flex items-start gap-4">
                <div className="h-12 w-12 rounded-lg bg-gray-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-5 w-3/4 rounded bg-gray-200" />
                  <div className="h-3 w-1/3 rounded bg-gray-200" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : data && data.stories.length > 0 ? (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Showing {offset + 1}-{Math.min(offset + limit, data.total)} of{" "}
              {data.total} stories
            </p>
          </div>
          <div className="space-y-3">
            {data.stories.map((story: Story) => {
              const domain = getDomainFromUrl(story.url);

              return (
                <article key={story.id} className="card flex items-start gap-4">
                  {/* Score Badge */}
                  <div
                    className={`flex h-12 w-12 flex-shrink-0 flex-col items-center justify-center rounded-lg ${scoreColor(story.score)}`}
                  >
                    <span className="text-lg font-bold leading-none">
                      {story.score}
                    </span>
                    <span className="text-[10px] uppercase tracking-wide">pts</span>
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-2">
                      <a
                        href={story.url || `https://news.ycombinator.com/item?id=${story.hn_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-base font-semibold text-gray-900 hover:text-accent"
                      >
                        {story.title}
                      </a>
                    </div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <span>by {story.author}</span>
                      <span>{new Date(story.posted_at).toLocaleDateString()}</span>
                      {domain && (
                        <span className="badge-blue">{domain}</span>
                      )}
                      {story.descendants > 0 && (
                        <span className="flex items-center gap-1">
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.686-.789 2.868 2.868 0 002.001-2.264V6.364a2.868 2.868 0 00-2.001-2.264 48.304 48.304 0 00-5.686-.789 1.527 1.527 0 00-1.037.443L7.5 15.75V5.478" />
                          </svg>
                          {story.descendants}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* HN Link */}
                  <a
                    href={`https://news.ycombinator.com/item?id=${story.hn_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-xs font-medium text-accent hover:text-accent-dark"
                  >
                    HN
                  </a>
                </article>
              );
            })}
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
          <p className="text-gray-500">No stories found</p>
        </div>
      )}
    </div>
  );
}
