"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { TrendingTopic } from "@/lib/types";

interface TrendingChartProps {
  topics: TrendingTopic[];
  loading: boolean;
}

const SOURCE_COLORS: Record<string, string> = {
  papers: "#3b82f6",
  repos: "#22c55e",
  stories: "#f97316",
  all: "#6366f1",
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  const data = payload[0].payload as TrendingTopic;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg">
      <p className="text-sm font-semibold text-gray-900">{label}</p>
      <p className="text-sm text-gray-600">Count: {data.count}</p>
      <p className="text-sm text-gray-600 capitalize">Source: {data.source}</p>
    </div>
  );
}

export default function TrendingChart({ topics, loading }: TrendingChartProps) {
  if (loading) {
    return (
      <div className="card">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Trending Topics</h3>
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-accent" />
        </div>
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className="card">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Trending Topics</h3>
        <div className="flex h-64 items-center justify-center">
          <p className="text-gray-500">No trending data available</p>
        </div>
      </div>
    );
  }

  const chartData = topics.map((t) => ({
    name: t.topic.length > 18 ? t.topic.slice(0, 18) + "..." : t.topic,
    count: t.count,
    source: t.source,
    fullName: t.topic,
  }));

  return (
    <div className="card">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Trending Topics</h3>
        <div className="flex gap-3 text-xs">
          {Object.entries(SOURCE_COLORS).map(([source, color]) => (
            <span key={source} className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="capitalize text-gray-500">{source}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: "#64748b" }}
              angle={-35}
              textAnchor="end"
              interval={0}
            />
            <YAxis tick={{ fontSize: 12, fill: "#64748b" }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={SOURCE_COLORS[entry.source] ?? "#6366f1"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
