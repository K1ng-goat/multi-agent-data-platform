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
interface KpiItem { label: string; value: string; icon: string; change: string }
interface ChartData {
  type: "line" | "bar" | "pie";
  title: string;
  labels: string[];
  datasets: { name: string; data: number[] }[];
}
interface DashboardData {
  has_data: boolean;
  filename?: string;
  session_id?: string;
  updated_at?: string;
  kpi: KpiItem[];
  charts: ChartData[];
  ai_summary: string;
  ai_trend: string;
  ai_anomaly: string;
  columns_list: string[];
}

const CHART_COLORS = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"];
const KPI_ICONS: Record<string, string> = {
  rows: "📊", columns: "📋", anomaly: "⚠️", ai: "🤖",
};

// --- Sub-components ---
function KpiCard({ item }: { item: KpiItem }) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 flex items-start justify-between">
      <div>
        <p className="text-xs text-zinc-400 dark:text-zinc-500 mb-1">{item.label}</p>
        <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">{item.value}</p>
        {item.change && <p className="text-[11px] text-emerald-500 mt-0.5">{item.change}</p>}
      </div>
      <span className="text-2xl">{KPI_ICONS[item.icon] || "📌"}</span>
    </div>
  );
}

function DashboardChart({ chart }: { chart: ChartData }) {
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

// --- Main Page ---
export default function AnalyticsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
      return;
    }
    if (!user) return;
    apiFetch(`${API_BASE}/dashboard`)
      .then((r) => r.json())
      .then((d) => setData(d))
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

  if (loading) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-zinc-400">加载分析数据中...</p>
        </div>
      </div>
    );
  }

  if (!data || !data.has_data) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center max-w-md">
          <span className="text-5xl mb-4 block">🏠</span>
          <h2 className="text-xl font-bold text-zinc-800 dark:text-zinc-200 mb-2">概览</h2>
          <p className="text-sm text-zinc-500 mb-6">在工作区上传 Excel 文件进行 AI 分析后，分析概览将在此展示。</p>
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
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">首页</h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              最近分析：{data.filename}
              {data.updated_at && <> · {new Date(data.updated_at).toLocaleString("zh-CN")}</>}
            </p>
          </div>
          <Link href="/" className="text-sm text-blue-600 dark:text-blue-400 hover:underline">
            分析新文件 →
          </Link>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {data.kpi.map((item, i) => (<KpiCard key={i} item={item} />))}
        </div>

        {/* Charts */}
        {data.charts.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.charts.slice(0, 4).map((chart, i) => (
              <DashboardChart key={i} chart={chart} />
            ))}
          </div>
        )}

        {/* AI Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
            <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">AI 分析摘要</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed whitespace-pre-wrap">
              {data.ai_summary || "暂无 AI 分析结果，请上传文件进行分析。"}
            </p>
          </div>
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5">
            <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">数据概览</h3>
            <div className="space-y-3">
              <div>
                <p className="text-[10px] text-zinc-400 uppercase">文件</p>
                <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 truncate">{data.filename}</p>
              </div>
              <div>
                <p className="text-[10px] text-zinc-400 uppercase">数据列</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {data.columns_list.slice(0, 8).map((col, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                      {col}
                    </span>
                  ))}
                  {data.columns_list.length > 8 && (
                    <span className="text-[10px] text-zinc-400">+{data.columns_list.length - 8} 更多</span>
                  )}
                </div>
              </div>
              {data.ai_trend && (
                <div>
                  <p className="text-[10px] text-zinc-400 uppercase">趋势</p>
                  <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-0.5 line-clamp-2">{data.ai_trend}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
