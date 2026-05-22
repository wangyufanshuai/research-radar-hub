"use client";

import { useEffect, useState, useCallback } from "react";
import { fetchPapers } from "@/lib/api";
import type { Paper, PapersResponse } from "@/lib/types";

const ARXIV_CATEGORIES = [
  "",
  "cs.AI",
  "cs.CL",
  "cs.CV",
  "cs.LG",
  "cs.NE",
  "cs.SE",
  "math.CO",
  "physics.comp-ph",
  "q-bio.QM",
  "stat.ML",
];

export default function PapersPage() {
  const [data, setData] = useState<PapersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [category, setCategory] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadPapers = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchPapers({ keyword, category, offset, limit });
      setData(result);
    } catch (err) {
      console.error("Failed to fetch papers:", err);
    } finally {
      setLoading(false);
    }
  }, [keyword, category, offset]);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setKeyword(searchInput);
    setOffset(0);
  }

  function handleCategoryChange(value: string) {
    setCategory(value);
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
        <h1 className="text-2xl font-bold text-gray-900">Papers</h1>
        <p className="mt-1 text-sm text-gray-500">
          Research papers collected from arXiv
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col gap-4 sm:flex-row">
          <form onSubmit={handleSearch} className="flex-1">
            <div className="flex gap-2">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search papers by keyword..."
                className="input-field"
              />
              <button type="submit" className="btn-primary whitespace-nowrap">
                Search
              </button>
            </div>
          </form>
          <select
            value={category}
            onChange={(e) => handleCategoryChange(e.target.value)}
            className="input-field w-full sm:w-48"
          >
            <option value="">All Categories</option>
            {ARXIV_CATEGORIES.filter(Boolean).map((cat) => (
              <option key={cat} value={cat}>
                {cat}
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
                <div className="h-5 w-3/4 rounded bg-gray-200" />
                <div className="h-3 w-1/2 rounded bg-gray-200" />
                <div className="h-3 w-full rounded bg-gray-200" />
                <div className="h-3 w-5/6 rounded bg-gray-200" />
              </div>
            </div>
          ))}
        </div>
      ) : data && data.papers.length > 0 ? (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              Showing {offset + 1}-{Math.min(offset + limit, data.total)} of{" "}
              {data.total} papers
            </p>
          </div>
          <div className="space-y-4">
            {data.papers.map((paper: Paper) => (
              <article key={paper.id} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-base font-semibold text-gray-900 hover:text-accent"
                    >
                      {paper.title}
                    </a>
                    <p className="mt-1 text-sm text-gray-500">
                      {paper.authors.join(", ")}
                    </p>
                    <p className="mt-2 line-clamp-2 text-sm text-gray-600">
                      {paper.abstract}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <span className="badge-blue">{paper.category}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(paper.published_date).toLocaleDateString()}
                      </span>
                      <span className="text-xs text-gray-400">
                        arXiv: {paper.arxiv_id}
                      </span>
                    </div>
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
          <p className="text-gray-500">No papers found</p>
        </div>
      )}
    </div>
  );
}
