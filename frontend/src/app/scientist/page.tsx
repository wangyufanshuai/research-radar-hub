"use client";

import { useEffect, useMemo, useState } from "react";
import { createScientistTask, fetchScientistTask, fetchScientistTasks, runScientistTask } from "@/lib/api";
import type { PaperUnderstanding, ScientistArtifact, ScientistTask, ScientistTaskDetail, ScientistTaskItem } from "@/lib/types";

const stageOrder = ["Planner", "Scout", "Deduplicator", "NoveltyScorer", "Reproducer", "Writer"];

function scoreClass(value: number) {
  if (value >= 7) return "text-green-700";
  if (value >= 4) return "text-orange-700";
  return "text-gray-600";
}

function latestArtifact(task: ScientistTaskDetail | null, kind: string): ScientistArtifact | undefined {
  return task?.artifacts
    .filter((artifact) => artifact.kind === kind)
    .sort((a, b) => new Date(b.created_at_artifact).getTime() - new Date(a.created_at_artifact).getTime())[0];
}

function parseList(value?: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

function UnderstandingPanel({ items }: { items: ScientistTaskItem[] }) {
  const understandings = items.map((item) => item.understanding).filter(Boolean) as PaperUnderstanding[];
  const datasets = understandings.flatMap((item) => parseList(item.dataset_mentions));
  const code = understandings.flatMap((item) => parseList(item.code_mentions));
  const formulas = understandings.flatMap((item) => parseList(item.formula_candidates));
  const citations = understandings.flatMap((item) => parseList(item.citation_mentions));
  const metrics = understandings.flatMap((item) => parseList(item.metric_mentions));
  const groups = [
    ["Datasets / benchmarks", datasets],
    ["Code links", code],
    ["Formula candidates", formulas],
    ["Citation clues", citations],
    ["Metrics", metrics],
  ] as const;
  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900">Paper Understanding Signals</h2>
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        {groups.map(([title, values]) => (
          <div key={title} className="rounded-lg border border-gray-200 p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</div>
            <ul className="mt-2 space-y-1 text-xs text-gray-700">
              {Array.from(new Set(values)).slice(0, 5).map((value) => (
                <li key={value} className="line-clamp-2">- {value}</li>
              ))}
              {values.length === 0 && <li className="text-gray-400">No signal yet.</li>}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function ItemTable({ title, items }: { title: string; items: ScientistTaskItem[] }) {
  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
              <th className="px-3 py-2">Title</th>
              <th className="px-3 py-2">Rel</th>
              <th className="px-3 py-2">Novelty</th>
              <th className="px-3 py-2">Repro</th>
              <th className="px-3 py-2">Signals</th>
              <th className="px-3 py-2">Selected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {items.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-gray-500" colSpan={6}>
                  No candidates yet.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={`${item.source}-${item.source_id}`}>
                  <td className="max-w-xl px-3 py-3">
                    <a className="font-medium text-accent hover:underline" href={item.url ?? "#"} target="_blank">
                      {item.title}
                    </a>
                    {item.summary && <p className="mt-1 line-clamp-2 text-xs text-gray-500">{item.summary}</p>}
                  </td>
                  <td className={`px-3 py-3 font-semibold ${scoreClass(item.relevance_score)}`}>{item.relevance_score.toFixed(1)}</td>
                  <td className={`px-3 py-3 font-semibold ${scoreClass(item.novelty_score)}`}>{item.novelty_score.toFixed(1)}</td>
                  <td className={`px-3 py-3 font-semibold ${scoreClass(item.reproducibility_score)}`}>{item.reproducibility_score.toFixed(1)}</td>
                  <td className="px-3 py-3 text-xs text-gray-500">{item.understanding?.understanding_status ?? "-"}</td>
                  <td className="px-3 py-3">{item.selected ? <span className="badge-green">yes</span> : <span className="badge-orange">review</span>}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ScientistPage() {
  const [topic, setTopic] = useState("neural operator for relativistic hydrodynamics");
  const [useLlm, setUseLlm] = useState(true);
  const [running, setRunning] = useState(false);
  const [task, setTask] = useState<ScientistTaskDetail | null>(null);
  const [history, setHistory] = useState<ScientistTask[]>([]);
  const [sourceFilter, setSourceFilter] = useState<"all" | "arxiv" | "github" | "nasa">("all");
  const [error, setError] = useState<string | null>(null);

  const visibleItems = useMemo(() => {
    const items = task?.items ?? [];
    return sourceFilter === "all" ? items : items.filter((item) => item.source === sourceFilter);
  }, [task, sourceFilter]);
  const papers = useMemo(() => visibleItems.filter((item) => item.source === "arxiv"), [visibleItems]);
  const repos = useMemo(() => visibleItems.filter((item) => item.source === "github"), [visibleItems]);
  const nasa = useMemo(() => visibleItems.filter((item) => item.source === "nasa"), [visibleItems]);
  const readingRoute = latestArtifact(task, "reading_route");
  const experimentPlan = latestArtifact(task, "experiment_plan");
  const report = latestArtifact(task, "report");

  useEffect(() => {
    fetchScientistTasks(0, 8)
      .then((data) => setHistory(data.items))
      .catch(() => setHistory([]));
  }, []);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const created = await createScientistTask(topic, useLlm);
      const detail = await runScientistTask(created.id, { max_papers: 20, max_repos: 10, use_llm: useLlm });
      setTask(detail);
      const list = await fetchScientistTasks(0, 8).catch(() => null);
      if (list) setHistory(list.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run AI Scientist task");
    } finally {
      setRunning(false);
    }
  }

  async function openTask(taskId: number) {
    setRunning(true);
    setError(null);
    try {
      setTask(await fetchScientistTask(taskId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AI Scientist task");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Scientist Workspace</h1>
        <p className="mt-1 text-sm text-gray-500">
          Create a staged research workflow: plan, scout, deduplicate, score novelty, and draft a reproduction plan.
        </p>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900">Recent Tasks</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {history.length === 0 ? (
            <span className="text-sm text-gray-500">No prior tasks found.</span>
          ) : (
            history.map((item) => (
              <button key={item.id} className="btn-secondary text-left" onClick={() => openTask(item.id)}>
                #{item.id} {item.topic.slice(0, 48)} - {item.status}
              </button>
            ))
          )}
        </div>
      </div>

      <div className="card">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <div>
            <label className="text-sm font-medium text-gray-700">Research topic</label>
            <input className="input-field mt-2" value={topic} onChange={(event) => setTopic(event.target.value)} />
          </div>
          <div className="flex items-end gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={useLlm} onChange={(event) => setUseLlm(event.target.checked)} />
              LLM enhance
            </label>
            <button className="btn-primary min-w-36 disabled:opacity-50" onClick={handleRun} disabled={running || topic.trim().length < 3}>
              {running ? "Running..." : "Run workspace"}
            </button>
          </div>
        </div>
        {error && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      </div>

      <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
        {stageOrder.map((stage) => {
          const run = task?.runs.find((item) => item.stage === stage);
          const status = run?.status ?? "pending";
          return (
            <div key={stage} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{stage}</div>
              <div className={`mt-2 text-sm font-semibold ${status === "success" ? "text-green-700" : status === "failed" ? "text-red-700" : "text-gray-700"}`}>
                {status}
              </div>
            </div>
          );
        })}
      </div>

      {task && (
        <>
          {task.error_message && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{task.error_message}</div>}
          <div className="flex flex-wrap items-center gap-2">
            {(["all", "arxiv", "github", "nasa"] as const).map((source) => (
              <button
                key={source}
                className={sourceFilter === source ? "btn-primary" : "btn-secondary"}
                onClick={() => setSourceFilter(source)}
              >
                {source}
              </button>
            ))}
          </div>
          <UnderstandingPanel items={task.items} />
          <div className="grid gap-6 xl:grid-cols-2">
            <ItemTable title="Candidate Papers" items={papers} />
            <ItemTable title="Candidate GitHub Repositories" items={repos} />
          </div>
          <ItemTable title="Candidate NASA Signals" items={nasa} />

          <div className="grid gap-6 xl:grid-cols-2">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900">Reading Route</h2>
              <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-800">
                {readingRoute?.body_markdown ?? "No reading route generated yet."}
              </pre>
            </div>
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900">Reproduction Plan</h2>
              <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-800">
                {experimentPlan?.body_markdown ?? "No experiment plan generated yet."}
              </pre>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900">Report Artifact</h2>
            <p className="mt-2 text-sm text-gray-600">{report?.html_path ?? "No report path available."}</p>
            <pre className="mt-4 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-800">
              {report?.body_markdown ?? "No report generated yet."}
            </pre>
          </div>
        </>
      )}
    </div>
  );
}
