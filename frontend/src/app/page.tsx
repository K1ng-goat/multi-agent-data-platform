"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import type {
  ThemeInfo, StyleConfig, ChartData, AnalyzeResult,
  ToolStep, WorkflowTimelineStep, WorkflowPlan, AgentStep, ChatMessage,
} from "@/lib/WorkspaceContext";

const COLORS = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"];
const TOOL_LABELS: Record<string, string> = {
  compute_stat: "计算统计", sort_data: "排序查询", group_by: "分组汇总",
  analyze_trend: "趋势分析", filter_data: "条件筛选", describe_data: "数据概览",
};
const STATUS_ICONS: Record<string, string> = { done: "✓", running: "●", error: "✗", pending: "○" };
const STATUS_COLORS: Record<string, string> = {
  done: "text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-900/20 dark:border-green-800",
  running: "text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-900/20 dark:border-blue-800",
  error: "text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-900/20 dark:border-red-800",
  pending: "text-zinc-400 bg-zinc-50 border-zinc-200 dark:text-zinc-500 dark:bg-zinc-800 dark:border-zinc-700",
};

// --- Sub-components ---
function ThemeSelector({ themes, config, onSelect }: {
  themes: ThemeInfo[];
  config: StyleConfig;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="bg-white dark:bg-zinc-900 p-4 rounded-lg border border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-sm font-semibold text-black dark:text-zinc-50">文档风格</h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            当前：{config.themeName}
            <span className="ml-1">| 标题字体：{config.titleFont} | 正文字体：{config.bodyFont}</span>
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <select value={config.activeTheme} onChange={(e) => onSelect(e.target.value)}
          className="text-sm border border-zinc-200 dark:border-zinc-700 rounded-md px-3 py-1.5 bg-white dark:bg-zinc-800 text-black dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-blue-500">
          {themes.map(t => (
            <option key={t.id} value={t.id}>{t.name} — {t.description}</option>
          ))}
        </select>
        {/* Color swatch preview */}
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-zinc-400 mr-1">色板:</span>
          {config.chartColors.slice(0, 4).map((color, i) => (
            <span key={i} className="w-4 h-4 rounded-full border border-zinc-300 dark:border-zinc-600" style={{ backgroundColor: color }} />
          ))}
          <span className="w-4 h-4 rounded-full border border-zinc-300 dark:border-zinc-600" style={{ backgroundColor: config.headerBg }} />
        </div>
        <p className="text-[10px] text-zinc-400">提示：在对话中输入"使用商务风格"或"标题用黑体三号"来动态调整样式</p>
      </div>
    </div>
  );
}

function ChartCard({ chart }: { chart: ChartData }) {
  const data = chart.labels.map((label, i) => {
    const row: Record<string, string | number> = { label };
    chart.datasets.forEach((ds) => { row[ds.name] = ds.data[i] ?? 0; });
    return row;
  });
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
      <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">{chart.title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          {chart.type === "line" ? (
            <LineChart data={data}>
              <XAxis dataKey="label" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
              {chart.datasets.map((ds, i) => (<Line key={ds.name} type="monotone" dataKey={ds.name} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />))}
            </LineChart>
          ) : chart.type === "bar" ? (
            <BarChart data={data}>
              <XAxis dataKey="label" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
              {chart.datasets.map((ds, i) => (<Bar key={ds.name} dataKey={ds.name} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />))}
            </BarChart>
          ) : (
            <PieChart>
              <Pie data={data} dataKey={chart.datasets[0]?.name} nameKey="label" cx="50%" cy="50%" outerRadius={80} label>
                {data.map((_, i) => (<Cell key={i} fill={COLORS[i % COLORS.length]} />))}
              </Pie>
              <Tooltip /><Legend />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ToolCallBadge({ step }: { step: ToolStep }) {
  const label = TOOL_LABELS[step.tool] || step.tool;
  const argsStr = Object.entries(step.args).map(([k, v]) => `${k}=${v}`).join(", ");
  return (
    <div className="mb-1.5 text-xs">
      <span className="inline-flex items-center gap-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md px-2.5 py-1">
        <span className="text-blue-600 dark:text-blue-400">&#9881;</span>
        <span className="font-medium text-blue-700 dark:text-blue-300">{label}</span>
        <span className="text-blue-500 dark:text-blue-400">({argsStr})</span>
      </span>
    </div>
  );
}

function WorkflowTimeline({ plan, timeline }: { plan: WorkflowPlan; timeline: WorkflowTimelineStep[] }) {
  const steps = plan.steps.map((s, i) => {
    const executed = timeline[i];
    return {
      name: s.name, tool: s.tool, args: s.args,
      status: executed?.status || "pending",
      result: executed?.result,
    };
  });
  return (
    <div className="mb-3 p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
      <div className="space-y-0">
        {steps.map((s, i) => {
          const colorCls = STATUS_COLORS[s.status] || STATUS_COLORS.pending;
          return (
            <div key={i} className="flex items-start gap-2.5">
              <div className="flex flex-col items-center pt-0.5">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border ${colorCls}`}>
                  {s.status === "done" ? STATUS_ICONS.done : s.status === "running" ? STATUS_ICONS.running : s.status === "error" ? STATUS_ICONS.error : i + 1}
                </span>
                {i < steps.length - 1 && (
                  <div className={`w-0.5 h-5 ${s.status === "done" ? "bg-green-400" : "bg-zinc-200 dark:bg-zinc-600"}`} />
                )}
              </div>
              <div className="pb-3 flex-1 min-w-0">
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">{s.name}</span>
                <span className="text-[10px] text-zinc-400 ml-1.5">
                  {TOOL_LABELS[s.tool] || s.tool}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SafeAgentTimeline({ steps }: { steps: AgentStep[] | undefined }) {
  if (!steps || !Array.isArray(steps) || steps.length === 0) return null;
  try {
    return <AgentTimelineInner steps={steps} />;
  } catch {
    return <p className="text-xs text-zinc-400">(无法渲染Agent步骤)</p>;
  }
}

function AgentTimelineInner({ steps }: { steps: AgentStep[] }) {
  const AGENT_LABELS: Record<string, string> = {
    MasterAgent: "主控", DataAgent: "数据分析", ChartAgent: "图表生成",
    AuditAgent: "数据审计", ReportAgent: "报告生成", StyleAgent: "样式设置",
    ExportAgent: "文件导出",
  };
  return (
    <div className="mb-3 p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-100 dark:border-zinc-700">
      <div className="space-y-0">
        {steps.map((s, i) => {
          const colorCls = STATUS_COLORS[s.status] || STATUS_COLORS.pending;
          return (
            <div key={i} className="flex items-start gap-2.5">
              <div className="flex flex-col items-center pt-0.5">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border ${colorCls}`}>
                  {s.status === "done" ? STATUS_ICONS.done : s.status === "running" ? STATUS_ICONS.running : s.status === "error" ? STATUS_ICONS.error : i + 1}
                </span>
                {i < steps.length - 1 && (
                  <div className={`w-0.5 h-5 ${s.status === "done" ? "bg-green-400" : "bg-zinc-200 dark:bg-zinc-600"}`} />
                )}
              </div>
              <div className="pb-3 flex-1 min-w-0">
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">{AGENT_LABELS[s.agent] || s.agent}</span>
                <span className="text-[10px] text-zinc-400 ml-1.5">{s.message}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function IntentBadge({ mode }: { mode: "chat" | "workflow" | "agent" }) {
  if (mode === "agent") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-100 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800">
        &#9883; Agent
      </span>
    );
  }
  return mode === "workflow" ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-100 text-purple-700 border border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800">
      &#9883; Workflow
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-100 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800">
      &#9998; Chat
    </span>
  );
}

// --- Main ---
export default function Home() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const workspace = useWorkspace();

  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Derive local aliases for convenience
  const result = workspace.result;
  const messages = workspace.messages;
  const lastMode = workspace.lastMode;
  const agentMode = workspace.agentMode;
  const styleConfig = workspace.styleConfig;
  const themes = workspace.themes;

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    if (themes.length > 0) return; // already loaded
    apiFetch("http://localhost:8000/themes").then(r => r.json()).then(d => workspace.setThemes(d.themes || [])).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themes.length]);

  const refreshStyleConfig = async (sessionId: string) => {
    try {
      const r = await apiFetch(`http://localhost:8000/style/preview/${sessionId}`);
      if (!r.ok) return;
      const d = await r.json();
      const p = d.preview || {};
      workspace.setStyleConfig({
        activeTheme: d.active_theme || "business",
        themeName: p.theme_name || "商务风格",
        primaryColor: p.primary_color || "#1F4E79",
        headerBg: p.header_bg || "#1F4E79",
        headerFg: p.header_fg || "#FFFFFF",
        titleFont: p.title_font || "SimHei",
        bodyFont: p.body_font || "Microsoft YaHei",
        chartColors: p.chart_colors || ["#1F4E79"],
        overrides: d.style_overrides || {},
      });
    } catch { /* ignore */ }
  };

  useEffect(() => {
    if (!result?.session_id) return;
    refreshStyleConfig(result.session_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result?.session_id]);

  const applyTheme = async (themeId: string) => {
    if (!result?.session_id) return;
    try {
      const res = await apiFetch("http://localhost:8000/style/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: result.session_id, theme: themeId }),
      });
      if (res.ok) {
        await refreshStyleConfig(result.session_id);
      }
    } catch { /* ignore */ }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true); setError(null);
    workspace.setResult(null);
    workspace.clearMessages();
    workspace.setLastMode(null);
    try {
      const formData = new FormData(); formData.append("file", file);
      const res = await apiFetch("http://localhost:8000/analyze", { method: "POST", body: formData });
      if (!res.ok) throw new Error(`请求失败: ${res.statusText}`);
      workspace.setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally { setLoading(false); }
  };

  const sendMessage = async () => {
    if (!input.trim() || !result?.session_id || sending) return;
    const text = input.trim();
    setInput("");
    workspace.appendUserMessage(text);
    setSending(true);

    const endpoint = agentMode ? "agent-chat" : "chat";
    const bodyKey = agentMode ? "message" : "question";

    try {
      const res = await apiFetch(`http://localhost:8000/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: result.session_id,
          [bodyKey]: text,
          ...(agentMode ? { mode: "auto" } : {}),
        }),
      });
      const data = await res.json();

      // Validate response is not too large
      const dataStr = JSON.stringify(data);
      if (dataStr.length > 500000) {
        console.warn("[sendMessage] Response too large:", dataStr.length, "bytes — truncating");
      }

      const mode = agentMode ? "agent" : (data.mode || "chat");
      workspace.setLastMode(mode);

      // Sync style state when chat applies a style change
      if (data.style_applied || data.active_theme) {
        await refreshStyleConfig(result.session_id);
      }

      // Build safe message — ensure all fields are present and valid
      const safeReply = typeof data.reply === "string" ? data.reply.slice(0, 50000) : "无响应";
      const safeSteps = Array.isArray(data.steps) ? data.steps.slice(0, 50) : [];
      const safePlan = data.plan && typeof data.plan === "object" ? data.plan : undefined;
      const safeTimeline = Array.isArray(data.timeline) ? data.timeline.slice(0, 50) : undefined;

      workspace.appendAiMessage({
        role: "ai",
        content: safeReply,
        steps: [],
        mode: mode as "chat" | "workflow" | "agent",
        plan: safePlan,
        timeline: safeTimeline,
        agentSteps: safeSteps,
      });
    } catch (err) {
      console.error("[sendMessage] error:", err);
      workspace.appendAiMessage({ role: "ai", content: "请求失败，请重试。" });
    } finally { setSending(false); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const handleDownload = (path: string) => {
    window.open(`http://localhost:8000${path}`, "_blank");
  };

  if (authLoading || !user) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 items-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-col w-full max-w-6xl py-8 px-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-black dark:text-zinc-50">AI Excel Data Agent</h1>
          {workspace.hasWorkspace && (
            <button
              onClick={workspace.newWorkspace}
              className="px-4 py-2 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            >
              + New Workspace
            </button>
          )}
        </div>

        {/* Upload — only show when no active workspace */}
        {!workspace.hasWorkspace && (
          <div className="flex items-center gap-4 mb-6 bg-white dark:bg-zinc-900 p-5 rounded-lg border border-zinc-200 dark:border-zinc-800">
            <input type="file" accept=".xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-sm text-zinc-600 dark:text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-zinc-900 file:text-white dark:file:bg-zinc-100 dark:file:text-black hover:file:bg-zinc-700 dark:hover:file:bg-zinc-300" />
            <button onClick={handleUpload} disabled={!file || loading}
              className="px-5 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors">
              {loading ? "AI 分析中..." : "上传并 AI 分析"}
            </button>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-red-700 dark:text-red-400 text-sm">{error}</div>
        )}

        {result && (
          <div className="space-y-6">
            {/* File Info */}
            <div className="flex items-center gap-6 text-sm bg-white dark:bg-zinc-900 px-5 py-3 rounded-lg border border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-500">文件: <span className="text-black dark:text-zinc-50 font-medium">{result.data_summary.filename}</span></span>
              <span className="text-zinc-500">行数: <span className="text-black dark:text-zinc-50 font-medium">{result.data_summary.shape.rows}</span></span>
              <span className="text-zinc-500">列数: <span className="text-black dark:text-zinc-50 font-medium">{result.data_summary.shape.columns}</span></span>
            </div>

            {/* Theme Selector */}
            <ThemeSelector themes={themes} config={styleConfig} onSelect={applyTheme} />

            {/* Charts */}
            {result.charts.length > 0 && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {result.charts.map((chart, i) => (<ChartCard key={i} chart={chart} />))}
              </div>
            )}

            {/* AI Analysis */}
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-lg border border-zinc-200 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-black dark:text-zinc-50 mb-4">AI 分析结果</h2>
              <div className="space-y-5">
                <div><h3 className="text-sm font-semibold text-blue-600 dark:text-blue-400 mb-1">数据总结</h3><p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">{result.analysis.summary || "暂无"}</p></div>
                <div><h3 className="text-sm font-semibold text-amber-600 dark:text-amber-400 mb-1">异常分析</h3><p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">{result.analysis.anomaly || "暂无"}</p></div>
                <div><h3 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-1">趋势分析</h3><p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed whitespace-pre-wrap">{result.analysis.trend || "暂无"}</p></div>
              </div>
            </div>

            {/* Download Buttons */}
            {result.session_id && (
              <div className="bg-white dark:bg-zinc-900 p-5 rounded-lg border border-zinc-200 dark:border-zinc-800">
                <h2 className="text-lg font-semibold text-black dark:text-zinc-50 mb-3">导出下载</h2>
                <div className="flex flex-wrap gap-3">
                  <button onClick={() => handleDownload(`/export/excel/${result.session_id}`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-700 transition-colors">
                    <span>&#128196;</span> 导出 Excel
                  </button>
                  <button onClick={() => handleDownload(`/export/word/${result.session_id}`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
                    <span>&#128214;</span> 导出 Word 报告
                  </button>
                  {result.charts.map((_, i) => (
                    <button key={i} onClick={() => handleDownload(`/export/chart/${result.session_id}/${i}`)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 transition-colors">
                      <span>&#128247;</span> 图表 {i + 1}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-zinc-400 mt-2">生成的文件同时保存至 <code className="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-600 dark:text-zinc-400">backend/exports/</code> 文件夹</p>
              </div>
            )}

            {/* Chat Window */}
            <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 flex flex-col h-[550px]">
              <div className="px-5 py-3 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-black dark:text-zinc-50">数据对话</h2>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    {agentMode ? "Multi-Agent 模式：Master Agent 自动调度子Agent" : "AI 自动判断意图：简单问题→Chat，复杂任务→Workflow"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex rounded-md border border-zinc-200 dark:border-zinc-700 overflow-hidden">
                    <button
                      onClick={() => workspace.setAgentMode(false)}
                      className={`px-3 py-1 text-xs font-medium transition-colors ${!agentMode ? "bg-black text-white dark:bg-white dark:text-black" : "bg-white dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700"}`}
                    >
                      Chat
                    </button>
                    <button
                      onClick={() => workspace.setAgentMode(true)}
                      className={`px-3 py-1 text-xs font-medium transition-colors ${agentMode ? "bg-emerald-600 text-white" : "bg-white dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700"}`}
                    >
                      Agent
                    </button>
                  </div>
                  {lastMode && <IntentBadge mode={lastMode} />}
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                {messages.length === 0 && (
                  <p className="text-sm text-zinc-400 text-center py-8">
                    上传 Excel 后即可开始对话。试试"利润是多少"或"生成分析报告"。
                  </p>
                )}
                <ErrorBoundary>
                  {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user" ? "bg-black text-white dark:bg-white dark:text-black" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                    }`}>
                      {/* Agent timeline (for agent mode) — safe wrapped */}
                      {msg.mode === "agent" && (
                        <SafeAgentTimeline steps={msg.agentSteps} />
                      )}
                      {/* Workflow timeline (before the report) */}
                      {msg.mode === "workflow" && msg.plan && msg.timeline && (
                        <WorkflowTimeline plan={msg.plan} timeline={msg.timeline} />
                      )}
                      {/* Tool call badges (for chat mode) */}
                      {msg.mode !== "workflow" && msg.steps && msg.steps.length > 0 && (
                        <div className="mb-1.5">{msg.steps.map((step, j) => (<ToolCallBadge key={j} step={step} />))}</div>
                      )}
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  </div>
                ))}
                </ErrorBoundary>
                {sending && (
                  <div className="flex justify-start">
                    <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg px-4 py-2.5 text-sm">
                      <span className="inline-flex items-center gap-2 text-zinc-500">
                        <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                        思考中...
                      </span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input */}
              <div className="px-5 py-3 border-t border-zinc-200 dark:border-zinc-800 flex gap-2">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
                  placeholder="输入问题或任务，AI 自动判断意图..."
                  disabled={!result?.session_id}
                  className="flex-1 px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-md bg-white dark:bg-zinc-800 text-black dark:text-zinc-50 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50" />
                <button onClick={sendMessage} disabled={!input.trim() || sending || !result?.session_id}
                  className="px-4 py-2 rounded-md bg-black text-white dark:bg-white dark:text-black text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors">
                  发送
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
