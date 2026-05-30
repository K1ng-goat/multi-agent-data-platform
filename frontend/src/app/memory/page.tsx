"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/lib/AuthContext";
import { apiFetch } from "@/lib/api";

interface MemorySummary {
  total_analyses: number;
  total_workspaces: number;
  total_conversations: number;
  preferences_count: number;
  analyzed_files: string[];
  chart_types: Record<string, number>;
  last_active: string;
}

export default function MemoryPage() {
  const { user, loading: authLoading } = useAuth();
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [preferences, setPreferences] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [clearing, setClearing] = useState<string | null>(null);
  const [error, setError] = useState("");

  const fetchData = useCallback(() => {
    if (!user) return;
    setLoading(true);
    setError("");
    apiFetch("http://localhost:8000/memory/summary")
      .then(r => r.json())
      .then(d => setSummary(d))
      .catch(() => setError("无法加载 AI 记忆摘要"))
      .finally(() => setLoading(false));

    apiFetch("http://localhost:8000/memory/preferences")
      .then(r => r.json())
      .then(d => setPreferences(d.preferences || {}))
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!user) return;
    fetchData();
  }, [user, fetchData]);

  const handleClear = async (type: string) => {
    setClearing(type);
    setError("");
    try {
      const res = await apiFetch("http://localhost:8000/memory/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type }),
      });
      const data = await res.json();
      if (data.ok) {
        fetchData();
      } else {
        setError("清除失败，请重试");
      }
    } catch {
      setError("清除失败，请检查网络连接");
    } finally {
      setClearing(null);
    }
  };

  const handleSavePreference = async (key: string) => {
    try {
      await apiFetch("http://localhost:8000/memory/preferences", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: "preference", key, value: editValue }),
      });
      setPreferences(prev => ({ ...prev, [key]: editValue }));
      setEditingKey(null);
      setEditValue("");
      setError("");
    } catch {
      setError("保存偏好失败");
    }
  };

  const handleDeletePreference = async (key: string) => {
    try {
      await apiFetch("http://localhost:8000/memory/preferences", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      const updated = { ...preferences };
      delete updated[key];
      setPreferences(updated);
      setError("");
    } catch {
      setError("删除偏好失败");
    }
  };

  const handleAddPreference = () => {
    const key = prompt("输入偏好名称（例如：preferred_chart_type）：");
    if (!key || !key.trim()) return;
    const value = prompt("输入偏好值：");
    if (value === null) return;
    setEditingKey(null);
    apiFetch("http://localhost:8000/memory/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: "preference", key: key.trim(), value }),
    })
      .then(() => fetchData())
      .catch(() => setError("添加偏好失败"));
  };

  if (authLoading || !user) {
    return (
      <div className="flex-1 bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 bg-zinc-50 dark:bg-black overflow-auto">
      <div className="max-w-4xl mx-auto py-8 px-6 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">AI Memory</h1>
          <p className="text-sm text-zinc-500 mt-1">AI 记忆与偏好系统 — 管理 AI 学到的知识和个人偏好</p>
        </div>

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-600 dark:text-red-400">
            {error}
            <button onClick={() => setError("")} className="ml-2 underline">关闭</button>
          </div>
        )}

        {/* AI Memory Summary */}
        <section>
          <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200 mb-4">AI 记忆摘要</h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : summary ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                <StatCard label="分析次数" value={summary.total_analyses} color="blue" />
                <StatCard label="工作区记录" value={summary.total_workspaces} color="emerald" />
                <StatCard label="对话会话" value={summary.total_conversations} color="violet" />
                <StatCard label="偏好设置" value={summary.preferences_count} color="amber" />
                <StatCard label="最后活跃" value={summary.last_active ? summary.last_active.slice(0, 10) : "-"} color="zinc" />
              </div>
              {summary.analyzed_files.length > 0 && (
                <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 mb-6">
                  <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">分析过的文件</h3>
                  <div className="flex flex-wrap gap-2">
                    {summary.analyzed_files.map((f, i) => (
                      <span key={i} className="text-xs px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-8 text-center">
              <p className="text-sm text-zinc-400">暂无记忆数据。在 Workspace 中分析 Excel 文件后，AI 会自动记录分析结果。</p>
            </div>
          )}
        </section>

        {/* User Preferences */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200">AI 学习到的偏好</h2>
            <button
              onClick={handleAddPreference}
              className="text-xs px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              + 添加偏好
            </button>
          </div>
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
            {Object.keys(preferences).length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-sm text-zinc-400">AI 尚未学习到你的偏好</p>
                <p className="text-xs text-zinc-400 mt-1">随着使用次数的增加，AI 会自动从你的操作中学习偏好设置</p>
              </div>
            ) : (
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {Object.entries(preferences).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-3 px-5 py-3">
                    <span className="text-xs font-medium text-zinc-800 dark:text-zinc-200 min-w-[140px] max-w-[200px] truncate">
                      {key}
                    </span>
                    {editingKey === key ? (
                      <div className="flex-1 flex items-center gap-2">
                        <input
                          type="text"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          className="flex-1 text-xs px-2 py-1 rounded border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                          autoFocus
                        />
                        <button
                          onClick={() => handleSavePreference(key)}
                          className="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => { setEditingKey(null); setEditValue(""); }}
                          className="text-xs px-2 py-1 rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-300"
                        >
                          取消
                        </button>
                      </div>
                    ) : (
                      <>
                        <span className="flex-1 text-xs text-zinc-500 break-all">{String(value).slice(0, 300)}</span>
                        <button
                          onClick={() => { setEditingKey(key); setEditValue(String(value)); }}
                          className="text-xs text-blue-600 dark:text-blue-400 hover:underline shrink-0"
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => handleDeletePreference(key)}
                          className="text-xs text-red-500 hover:underline shrink-0"
                        >
                          删除
                        </button>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Memory Management */}
        <section>
          <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200 mb-4">Memory 管理</h2>
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 space-y-4">
            <p className="text-xs text-zinc-500">管理 AI 记忆数据。清除操作不可撤销，请谨慎操作。</p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleClear("analyses")}
                disabled={clearing === "analyses"}
                className="text-xs px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-red-50 hover:border-red-300 hover:text-red-600 disabled:opacity-50 transition-colors"
              >
                {clearing === "analyses" ? "清除中..." : "清除分析记忆"}
              </button>
              <button
                onClick={() => handleClear("workspaces")}
                disabled={clearing === "workspaces"}
                className="text-xs px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-red-50 hover:border-red-300 hover:text-red-600 disabled:opacity-50 transition-colors"
              >
                {clearing === "workspaces" ? "清除中..." : "清除工作区记忆"}
              </button>
              <button
                onClick={() => handleClear("preferences")}
                disabled={clearing === "preferences"}
                className="text-xs px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-red-50 hover:border-red-300 hover:text-red-600 disabled:opacity-50 transition-colors"
              >
                {clearing === "preferences" ? "清除中..." : "重置所有偏好"}
              </button>
              <button
                onClick={() => handleClear("all")}
                disabled={clearing === "all"}
                className="text-xs px-4 py-2 rounded-lg border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {clearing === "all" ? "清除中..." : "清除全部记忆"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colors: Record<string, string> = {
    blue: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400",
    emerald: "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400",
    violet: "bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800 text-violet-700 dark:text-violet-400",
    amber: "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400",
    zinc: "bg-zinc-50 dark:bg-zinc-900/40 border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400",
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color] || colors.zinc}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-1 opacity-70">{label}</p>
    </div>
  );
}
