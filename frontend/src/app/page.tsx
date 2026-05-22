"use client";

import { useEffect, useState } from "react";
import StatsCards from "@/components/dashboard/StatsCards";
import TrendingChart from "@/components/dashboard/TrendingChart";
import { fetchStats, fetchTrending, triggerCollect } from "@/lib/api";
import type { DashboardStats, TrendingTopic, CollectSource } from "@/lib/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [topics, setTopics] = useState<TrendingTopic[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [trendingLoading, setTrendingLoading] = useState(true);
  const [collecting, setCollecting] = useState<CollectSource | null>(null);

  useEffect(() => {
    fetchStats()
      .then((data) => setStats(data))
      .catch((err) => console.error("Failed to fetch stats:", err))
      .finally(() => setStatsLoading(false));

    fetchTrending(7)
      .then((data) => setTopics(data.topics))
      .catch((err) => console.error("Failed to fetch trending:", err))
      .finally(() => setTrendingLoading(false));
  }, []);

  async function handleCollect(source: CollectSource) {
    setCollecting(source);
    try {
      await triggerCollect(source);
      const updatedStats = await fetchStats();
      setStats(updatedStats);
    } catch (err) {
      console.error(`Failed to collect ${source}:`, err);
    } finally {
      setCollecting(null);
    }
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Overview of collected papers, repositories, stories, courses, and reports
          </p>
        </div>
        <div className="flex gap-2">
          {(["arxiv", "github", "hn", "course", "all"] as CollectSource[]).map((source) => (
            <button
              key={source}
              onClick={() => handleCollect(source)}
              disabled={collecting !== null}
              className="btn-secondary flex items-center gap-2 capitalize disabled:opacity-50"
            >
              {collecting === source ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-accent" />
              ) : (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077l1.41-.513m14.095-5.13l1.41-.513M5.106 17.785l1.15-.964m11.49-9.642l1.149-.964M7.501 19.795l.75-1.3m7.5-12.99l.75-1.3m-6.063 16.658l.26-1.477m2.605-14.772l.26-1.477m0 17.726l-.26-1.477M10.698 4.614l-.26-1.477M16.5 19.794l-.75-1.299M7.5 4.205L6.75 2.906m9.944 15.04l-1.149-.964M7.5 7.243l-1.15-.964" />
                </svg>
              )}
              Collect {source}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Cards */}
      <StatsCards stats={stats} loading={statsLoading} />

      {/* Trending Chart */}
      <TrendingChart topics={topics} loading={trendingLoading} />

      {/* Last Updated */}
      {stats?.last_updated && (
        <p className="text-center text-xs text-gray-400">
          Last updated: {new Date(stats.last_updated).toLocaleString()}
        </p>
      )}
    </div>
  );
}
