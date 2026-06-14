"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { API_BASE } from "@/lib/config";

const AGENTS = ["DataAgent", "AuditAgent", "ChartAgent", "ReportAgent", "StyleAgent"];

export default function PlaygroundPage() {
  const [agent, setAgent] = useState("DataAgent");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleRun = async () => {
    if (!prompt.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await apiFetch(`${API_BASE}/agent/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent, prompt }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setError("Execution failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 bg-zinc-50 dark:bg-black overflow-auto">
      <div className="max-w-3xl mx-auto py-8 px-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Agent Playground</h1>
          <p className="text-sm text-zinc-500 mt-1">Test and debug individual agents</p>
        </div>

        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Agent</label>
            <select value={agent} onChange={e => setAgent(e.target.value)}
              className="w-full mt-1 text-sm border border-zinc-200 dark:border-zinc-700 rounded-md px-3 py-2 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50">
              {AGENTS.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">Prompt</label>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
              rows={3} placeholder="Enter your test prompt..."
              className="w-full mt-1 text-sm border border-zinc-200 dark:border-zinc-700 rounded-md px-3 py-2 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 resize-none" />
          </div>

          <button onClick={handleRun} disabled={loading || !prompt.trim()}
            className="px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {loading ? "Running..." : "Execute"}
          </button>
        </div>

        {error && <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-600">{error}</div>}

        {result && (
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Result</h3>
            <div className="grid grid-cols-4 gap-3 text-xs">
              <Stat label="Agent" value={result.agent} />
              <Stat label="Duration" value={`${result.duration_ms}ms`} />
              <Stat label="Score" value={String(result.score)} />
              <Stat label="Success" value={result.success ? "Yes" : "No"} />
            </div>
            <div>
              <p className="text-xs text-zinc-500 mb-1">Output</p>
              <pre className="text-xs bg-zinc-50 dark:bg-zinc-800 rounded p-3 overflow-auto max-h-64 whitespace-pre-wrap">
                {JSON.stringify(result.output, null, 2)}
              </pre>
            </div>
            <p className="text-xs text-zinc-400">Trace: {result.trace_id}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-3">
      <p className="text-zinc-400">{label}</p>
      <p className="font-medium text-zinc-900 dark:text-zinc-50 mt-0.5">{value}</p>
    </div>
  );
}
