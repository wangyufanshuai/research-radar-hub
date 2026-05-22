"use client";

import { useEffect, useState } from "react";
import { fetchResearchReport, triggerCollect } from "@/lib/api";
import type { DailyReport } from "@/lib/types";

export default function RadarPage() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadReport(refresh = false) {
    setRefreshing(refresh);
    setError(null);
    try {
      const data = await fetchResearchReport(refresh);
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function handleCollectAll() {
    setCollecting(true);
    setError(null);
    try {
      const result = await triggerCollect("all");
      if (result.status !== "success") {
        setError(result.error || "Collection completed with errors");
      }
      await loadReport(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to collect sources");
    } finally {
      setCollecting(false);
    }
  }

  useEffect(() => {
    loadReport(false);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Research Radar</h1>
          <p className="mt-1 text-sm text-gray-500">
            Daily report across papers, GitHub projects, and course sources
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => loadReport(true)}
            disabled={refreshing || collecting}
            className="btn-secondary disabled:opacity-50"
          >
            {refreshing ? "Refreshing..." : "Refresh report"}
          </button>
          <button
            onClick={handleCollectAll}
            disabled={collecting || refreshing}
            className="btn-primary disabled:opacity-50"
          >
            {collecting ? "Collecting..." : "Collect all"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="card">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-accent" />
          </div>
        ) : report ? (
          <div className="space-y-4">
            <div className="border-b border-gray-200 pb-4">
              <h2 className="text-xl font-semibold text-gray-900">{report.title}</h2>
              <p className="mt-1 text-sm text-gray-500">
                {report.report_date} · generated {new Date(report.created_at_report).toLocaleString()}
              </p>
            </div>
            <pre className="max-h-[640px] overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-800">
              {report.body_markdown}
            </pre>
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center text-gray-500">
            No research report available
          </div>
        )}
      </div>
    </div>
  );
}
