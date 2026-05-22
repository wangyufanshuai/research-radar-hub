"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
import { fetchTrending } from "@/lib/api";
import type { TrendingTopic } from "@/lib/types";

const PERIOD_OPTIONS = [
  { label: "Last 7 days", value: 7 },
  { label: "Last 14 days", value: 14 },
  { label: "Last 30 days", value: 30 },
  { label: "Last 90 days", value: 90 },
];

const SOURCE_COLORS: Record<string, string> = {
  papers: "#3b82f6",
  repos: "#22c55e",
  stories: "#f97316",
  all: "#6366f1",
};

interface ChartDataItem {
  name: string;
  count: number;
  source: string;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload as ChartDataItem;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-lg">
      <p className="font-semibold text-gray-900">{item.name}</p>
      <p className="mt-1 text-sm text-gray-600">
        Mentions: <span className="font-medium">{item.count}</span>
      </p>
      <p className="text-sm capitalize text-gray-600">
        Source: <span className="font-medium">{item.source}</span>
      </p>
    </div>
  );
}

function CustomLegend() {
  return (
    <div className="flex justify-center gap-6 pb-2">
      {Object.entries(SOURCE_COLORS).map(([source, color]) => (
        <span key={source} className="flex items-center gap-1.5 text-sm">
          <span
            className="inline-block h-3 w-3 rounded-sm"
            style={{ backgroundColor: color }}
          />
          <span className="capitalize text-gray-600">{source}</span>
        </span>
      ))}
    </div>
  );
}

export default function AnalysisPage() {
  const [topics, setTopics] = useState<TrendingTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(7);

  useEffect(() => {
    setLoading(true);
    fetchTrending(period)
      .then((data) => setTopics(data.topics))
      .catch((err) => console.error("Failed to fetch trending:", err))
      .finally(() => setLoading(false));
  }, [period]);

  const chartData: ChartDataItem[] = topics.map((t) => ({
    name: t.topic.length > 20 ? t.topic.slice(0, 20) + "..." : t.topic,
    count: t.count,
    source: t.source,
  }));

  const sourceBreakdown = topics.reduce<Record<string, number>>((acc, t) => {
    acc[t.source] = (acc[t.source] || 0) + t.count;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analysis</h1>
          <p className="mt-1 text-sm text-gray-500">
            Trending topics and insights across all data sources
          </p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          className="input-field w-44"
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Source Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {(["all"] as const).map((source) => (
          <div key={source} className="card flex items-center gap-4">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-lg"
              style={{ backgroundColor: SOURCE_COLORS[source] + "15" }}
            >
              <div
                className="h-4 w-4 rounded-full"
                style={{ backgroundColor: SOURCE_COLORS[source] }}
              />
            </div>
            <div>
              <p className="text-sm capitalize text-gray-500">{source}</p>
              <p className="text-xl font-bold text-gray-900">
                {sourceBreakdown[source] ?? 0} mentions
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Trending Topics Bar Chart */}
      {loading ? (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Trending Topics</h3>
          <div className="flex h-80 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-accent" />
          </div>
        </div>
      ) : topics.length > 0 ? (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">
            Trending Topics
          </h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 10, right: 20, left: 0, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "#64748b" }}
                  angle={-40}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fontSize: 12, fill: "#64748b" }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend content={<CustomLegend />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={SOURCE_COLORS[entry.source] ?? "#6366f1"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="card flex h-64 items-center justify-center">
          <p className="text-gray-500">No trending data available for this period</p>
        </div>
      )}

      {/* Topic Table */}
      {topics.length > 0 && (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">
            Topic Details
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-3 pr-4 font-semibold text-gray-600">Topic</th>
                  <th className="pb-3 pr-4 font-semibold text-gray-600">Source</th>
                  <th className="pb-3 font-semibold text-gray-600">Count</th>
                </tr>
              </thead>
              <tbody>
                {topics.map((topic, index) => (
                  <tr
                    key={`${topic.topic}-${topic.source}-${index}`}
                    className="border-b border-gray-100 last:border-0"
                  >
                    <td className="py-3 pr-4 font-medium text-gray-900">
                      {topic.topic}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize"
                        style={{
                          backgroundColor: SOURCE_COLORS[topic.source] + "15",
                          color: SOURCE_COLORS[topic.source],
                        }}
                      >
                        {topic.source}
                      </span>
                    </td>
                    <td className="py-3 font-medium text-gray-700">
                      {topic.count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
