"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";
import { API_BASE } from "@/lib/config";

// --- Types ---
interface ChartData {
  type: "line" | "bar" | "pie";
  title: string;
  labels: string[];
  datasets: { name: string; data: number[] }[];
}
interface ReportItem {
  id: string;
  filename: string;
  rows: number;
  columns: number;
  columns_list: string[];
  summary: string;
  anomaly: string;
  trend: string;
  charts: ChartData[];
  created_at: string;
}
interface ReportDetail extends ReportItem {}

const CHART_COLORS = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"];

// --- Sub-components ---
function ReportChart({ chart }: { chart: ChartData }) {
  const data = chart.labels.map((label, i) => {
    const row: Record<string, string | number> = { label };
    chart.datasets.forEach((ds) => { row[ds.name] = ds.data[i] ?? 0; });
    return row;
  });
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
      <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">{chart.title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          {chart.type === "line" ? (
            <LineChart data={data}>
              <XAxis dataKey="label" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              {chart.datasets.map((ds, i) => (
                <Line key={ds.name} type="monotone" dataKey={ds.name} stroke={CHART_COLORS[i]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          ) : chart.type === "bar" ? (
            <BarChart data={data}>
              <XAxis dataKey="label" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              {chart.datasets.map((ds, i) => (
                <Bar key={ds.name} dataKey={ds.name} fill={CHART_COLORS[i]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          ) : (
            <PieChart>
              <Pie data={data} dataKey={chart.datasets[0]?.name} nameKey="label" cx="50%" cy="50%" outerRadius={80} label>
                {data.map((_, i) => (<Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />))}
              </Pie>
              <Tooltip /><Legend />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ReportDetail({ report, onBack }: { report: ReportDetail; onBack: () => void }) {
  return (
    <div className="flex-1 bg-zinc-50 dark:bg-black">
      <div className="max-w-7xl mx-auto py-6 px-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <button onClick={onBack} className="text-sm text-blue-600 dark:text-blue-400 hover:underline mb-1 inline-block">
              &larr; 返回报告列表
            </button>
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">{report.filename}</h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              {report.rows} 行 · {report.columns} 列 · {report.created_at}
            </p>
          </div>
        </div>

        {/* Charts */}
        {report.charts.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {report.charts.map((chart, i) => (
              <ReportChart key={i} chart={chart} />
            ))}
          </div>
        )}

        {/* AI Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
            <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">AI 分析摘要</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap">
              {report.summary || "暂无摘要"}
            </p>
          </div>
          <div className="space-y-4">
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
              <h3 className="text-sm font-semibold text-amber-600 dark:text-amber-400 mb-2">异常分析</h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap">
                {report.anomaly || "暂无异常"}
              </p>
            </div>
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
              <h3 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">趋势分析</h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap">
                {report.trend || "暂无趋势分析"}
              </p>
            </div>
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
              <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2">数据列</h3>
              <div className="flex flex-wrap gap-1">
                {report.columns_list.slice(0, 10).map((col, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                    {col}
                  </span>
                ))}
                {report.columns_list.length > 10 && (
                  <span className="text-[10px] text-zinc-400">+{report.columns_list.length - 10} 更多</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Main Page ---
export default function ReportsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (!user) return;
    apiFetch(`${API_BASE}/reports`)
      .then((r) => r.json())
      .then((d) => setReports(d.reports || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [authLoading, user, router]);

  if (authLoading) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  if (selectedReport) {
    return <ReportDetail report={selectedReport} onBack={() => setSelectedReport(null)} />;
  }

  if (loading) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-zinc-400">加载报告列表...</p>
        </div>
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center max-w-md">
          <span className="text-5xl mb-4 block">📋</span>
          <h2 className="text-xl font-bold text-zinc-800 dark:text-zinc-200 mb-2">历史成果中心</h2>
          <p className="text-sm text-zinc-500 mb-6">暂无历史分析成果。在工作区中上传并分析 Excel 文件后，所有分析报告、图表和洞察将在此统一保存。</p>
          <Link href="/" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
            前往工作区 →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-zinc-50 dark:bg-black">
      <div className="max-w-7xl mx-auto py-6 px-6 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">历史报告</h1>
          <p className="text-xs text-zinc-400 mt-0.5">历史分析成果 · 共 {reports.length} 条记录</p>
        </div>

        {/* Reports List */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {reports.map((report) => (
            <button
              key={report.id}
              onClick={() => setSelectedReport(report)}
              className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 text-left hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 truncate flex-1 mr-2">
                  {report.filename}
                </h3>
                <span className="text-[10px] text-zinc-400 whitespace-nowrap">{report.created_at}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-zinc-500 mb-3">
                <span>{report.rows} 行</span>
                <span>{report.columns} 列</span>
                <span>{report.charts.length} 图表</span>
              </div>
              {report.summary && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed line-clamp-2">
                  {report.summary}
                </p>
              )}
              <div className="flex flex-wrap gap-1 mt-3">
                {report.columns_list.slice(0, 4).map((col, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400">
                    {col}
                  </span>
                ))}
                {report.columns_list.length > 4 && (
                  <span className="text-[10px] text-zinc-400">+{report.columns_list.length - 4}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
