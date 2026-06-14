"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { API_BASE } from "@/lib/config";

interface MetricItem { agent_name: string; runs: number; success_rate: number; avg_duration_ms: number; total_retries: number; }
interface EvalItem { agent_name: string; runs: number; avg_score: number; }
interface TraceItem { workflow_id: string; agent_count: number; step_count: number; success_rate: number; total_duration_ms: number; }
interface DashboardData { metrics: MetricItem[]; evaluations: EvalItem[]; latestTrace: TraceItem | null; agents: string[]; tools: { name: string }[]; models: { id: string; enabled: boolean }[]; }

export default function AgentDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch(`${API_BASE}/agent/metrics`).then(r => r.json()),
      apiFetch(`${API_BASE}/agent/evaluation`).then(r => r.json()),
      apiFetch(`${API_BASE}/workflow/latest`).then(r => r.json()),
      apiFetch(`${API_BASE}/agents`).then(r => r.json()),
      apiFetch(`${API_BASE}/tools`).then(r => r.json()),
      apiFetch(`${API_BASE}/models`).then(r => r.json()),
    ]).then(([metricsRes, evalRes, traceRes, agentsRes, toolsRes, modelsRes]) => {
      setData({
        metrics: Object.values(metricsRes.metrics || {}),
        evaluations: Object.values(evalRes.evaluations || {}),
        latestTrace: traceRes.error ? null : traceRes,
        agents: agentsRes.agents || [],
        tools: toolsRes.tools || [],
        models: modelsRes.models || [],
      });
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="flex-1 bg-zinc-50 dark:bg-black overflow-auto">
      <div className="max-w-6xl mx-auto py-8 px-6 space-y-8">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Agent Dashboard</h1>

        {/* 1. Agent Metrics */}
        <Section title="Agent Metrics" count={data?.metrics.length || 0}>
          <div className="overflow-auto"><table className="w-full text-xs">
            <thead><tr className="text-left text-zinc-500 border-b border-zinc-200 dark:border-zinc-800">
              <th className="py-2 pr-4">Agent</th><th className="py-2 pr-4">Runs</th><th className="py-2 pr-4">Success</th><th className="py-2 pr-4">Avg Duration</th><th className="py-2 pr-4">Retries</th>
            </tr></thead>
            <tbody>
              {(data?.metrics || []).map(m => (
                <tr key={m.agent_name} className="border-b border-zinc-100 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300">
                  <td className="py-2 pr-4 font-medium">{m.agent_name}</td>
                  <td className="py-2 pr-4">{m.runs}</td>
                  <td className="py-2 pr-4"><span className={m.success_rate >= 90 ? "text-emerald-500" : "text-amber-500"}>{m.success_rate}%</span></td>
                  <td className="py-2 pr-4">{m.avg_duration_ms}ms</td>
                  <td className="py-2 pr-4">{m.total_retries}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Section>

        {/* 2. Agent Evaluation */}
        <Section title="Agent Evaluation" count={data?.evaluations.length || 0}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(data?.evaluations || []).map(e => (
              <div key={e.agent_name} className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-3">
                <p className="text-xs text-zinc-500">{e.agent_name}</p>
                <p className="text-lg font-bold text-zinc-900 dark:text-zinc-50">{e.avg_score}</p>
                <p className="text-xs text-zinc-400">{e.runs} evaluations</p>
              </div>
            ))}
          </div>
        </Section>

        {/* 3. Workflow Activity */}
        {data?.latestTrace && (
          <Section title="Latest Workflow">
            <div className="grid grid-cols-5 gap-3">
              <KPI label="Workflow ID" value={data.latestTrace.workflow_id} />
              <KPI label="Agents" value={String(data.latestTrace.agent_count)} />
              <KPI label="Steps" value={String(data.latestTrace.step_count)} />
              <KPI label="Success" value={`${data.latestTrace.success_rate}%`} />
              <KPI label="Duration" value={`${data.latestTrace.total_duration_ms}ms`} />
            </div>
          </Section>
        )}

        {/* 4. System Inventory */}
        <Section title="System Inventory">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-2">Agents ({data?.agents.length})</p>
              <div className="flex flex-wrap gap-1">{data?.agents.map(a => <span key={a} className="text-xs px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">{a}</span>)}</div>
            </div>
            <div>
              <p className="text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-2">Tools ({data?.tools.length})</p>
              <div className="flex flex-wrap gap-1">{data?.tools.map(t => <span key={t.name} className="text-xs px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">{t.name}</span>)}</div>
            </div>
            <div>
              <p className="text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-2">Models ({data?.models.length})</p>
              <div className="flex flex-wrap gap-1">{data?.models.map(m => <span key={m.id} className={`text-xs px-2 py-0.5 rounded ${m.enabled ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400"}`}>{m.id}</span>)}</div>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, count, children }: { title: string; count?: number; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">
        {title} {count !== undefined && <span className="text-zinc-400 font-normal">({count})</span>}
      </h2>
      {children}
    </div>
  );
}

function KPI({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-3">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="text-sm font-bold text-zinc-900 dark:text-zinc-50 mt-0.5 truncate">{value}</p>
    </div>
  );
}
