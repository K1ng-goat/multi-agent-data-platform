"use client";

import { createContext, useContext, useState, useEffect, useCallback, useMemo, type ReactNode } from "react";

// --- Shared Types ---
export interface ChartData {
  type: "line" | "bar" | "pie";
  title: string;
  labels: string[];
  datasets: { name: string; data: number[] }[];
}
export interface Analysis { summary: string; anomaly: string; trend: string }
export interface AnalyzeResult {
  session_id: string;
  data_summary: { filename: string; shape: { rows: number; columns: number }; columns: string[] };
  charts: ChartData[];
  analysis: Analysis;
}
export interface ToolStep { tool: string; args: Record<string, unknown>; result: string }
export interface WorkflowTimelineStep { step: number; name: string; tool: string; args: Record<string, unknown>; result: string; status: string }
export interface WorkflowPlan { title: string; steps: { name: string; tool: string; args: Record<string, unknown> }[] }
export interface AgentStep { agent: string; status: string; message: string }
export interface ChatMessage {
  role: "user" | "ai";
  content: string;
  steps?: ToolStep[];
  mode?: "chat" | "workflow" | "agent";
  plan?: WorkflowPlan;
  timeline?: WorkflowTimelineStep[];
  agentSteps?: AgentStep[];
}
export interface ThemeInfo { id: string; name: string; description: string; primary_color: string }
export interface StyleConfig {
  activeTheme: string;
  themeName: string;
  primaryColor: string;
  headerBg: string;
  headerFg: string;
  titleFont: string;
  bodyFont: string;
  chartColors: string[];
  overrides: Record<string, unknown>;
}

const DEFAULT_STYLE_CONFIG: StyleConfig = {
  activeTheme: "business",
  themeName: "商务风格",
  primaryColor: "#1F4E79",
  headerBg: "#1F4E79",
  headerFg: "#FFFFFF",
  titleFont: "SimHei",
  bodyFont: "Microsoft YaHei",
  chartColors: ["#1F4E79", "#E67E22", "#27AE60", "#C0392B", "#8E44AD", "#2980B9"],
  overrides: {},
};

const STORAGE_KEY = "workspace_state";

interface PersistentWorkspaceState {
  result: AnalyzeResult | null;
  messages: ChatMessage[];
  lastMode: "chat" | "workflow" | "agent" | null;
  agentMode: boolean;
  styleConfig: StyleConfig;
  themes: ThemeInfo[];
}

interface WorkspaceContextValue extends PersistentWorkspaceState {
  setResult: (r: AnalyzeResult | null) => void;
  appendAiMessage: (msg: ChatMessage) => void;
  appendUserMessage: (content: string) => void;
  clearMessages: () => void;
  setLastMode: (m: "chat" | "workflow" | "agent" | null) => void;
  setAgentMode: (b: boolean) => void;
  setStyleConfig: (c: StyleConfig) => void;
  setThemes: (t: ThemeInfo[]) => void;
  newWorkspace: () => void;
  hasWorkspace: boolean;
}

function loadState(): PersistentWorkspaceState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistentWorkspaceState;
    if (parsed.result?.session_id) return parsed;
    return null;
  } catch {
    return null;
  }
}

function saveState(state: PersistentWorkspaceState) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch { /* quota exceeded — ignore */ }
}

function clearSavedState() {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch { /* ignore */ }
}

const WorkspaceContext = createContext<WorkspaceContextValue>({
  result: null,
  messages: [],
  lastMode: null,
  agentMode: false,
  styleConfig: DEFAULT_STYLE_CONFIG,
  themes: [],
  setResult: () => {},
  appendAiMessage: () => {},
  appendUserMessage: () => {},
  clearMessages: () => {},
  setLastMode: () => {},
  setAgentMode: () => {},
  setStyleConfig: () => {},
  setThemes: () => {},
  newWorkspace: () => {},
  hasWorkspace: false,
});

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [result, setResultRaw] = useState<AnalyzeResult | null>(null);
  const [messages, setMessagesRaw] = useState<ChatMessage[]>([]);
  const [lastMode, setLastModeRaw] = useState<"chat" | "workflow" | "agent" | null>(null);
  const [agentMode, setAgentModeRaw] = useState(false);
  const [styleConfig, setStyleConfigRaw] = useState<StyleConfig>(DEFAULT_STYLE_CONFIG);
  const [themes, setThemesRaw] = useState<ThemeInfo[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage on first mount
  useEffect(() => {
    const saved = loadState();
    if (saved) {
      if (saved.result) setResultRaw(saved.result);
      if (saved.messages?.length) setMessagesRaw(saved.messages);
      if (saved.lastMode) setLastModeRaw(saved.lastMode);
      if (saved.agentMode) setAgentModeRaw(saved.agentMode);
      if (saved.styleConfig) setStyleConfigRaw(saved.styleConfig);
      if (saved.themes?.length) setThemesRaw(saved.themes);
    }
    setHydrated(true);
  }, []);

  // Persist to localStorage on every state change (after hydration)
  useEffect(() => {
    if (!hydrated) return;
    saveState({ result, messages, lastMode, agentMode, styleConfig, themes });
  }, [result, messages, lastMode, agentMode, styleConfig, themes, hydrated]);

  const setResult = useCallback((r: AnalyzeResult | null) => setResultRaw(r), []);

  const appendAiMessage = useCallback((msg: ChatMessage) => {
    setMessagesRaw((prev) => [...prev, msg]);
  }, []);

  const appendUserMessage = useCallback((content: string) => {
    setMessagesRaw((prev) => [...prev, { role: "user", content }]);
  }, []);

  const clearMessages = useCallback(() => setMessagesRaw([]), []);

  const setLastMode = useCallback((m: "chat" | "workflow" | "agent" | null) => setLastModeRaw(m), []);

  const setAgentMode = useCallback((b: boolean) => setAgentModeRaw(b), []);

  const setStyleConfig = useCallback((c: StyleConfig) => setStyleConfigRaw(c), []);

  const setThemes = useCallback((t: ThemeInfo[]) => setThemesRaw(t), []);

  const newWorkspace = useCallback(() => {
    setResultRaw(null);
    setMessagesRaw([]);
    setLastModeRaw(null);
    setAgentModeRaw(false);
    setStyleConfigRaw(DEFAULT_STYLE_CONFIG);
    clearSavedState();
  }, []);

  const hasWorkspace = result !== null;

  const value = useMemo(() => ({
    result, messages, lastMode, agentMode, styleConfig, themes,
    setResult, appendAiMessage, appendUserMessage, clearMessages,
    setLastMode, setAgentMode, setStyleConfig, setThemes,
    newWorkspace, hasWorkspace,
  }), [result, messages, lastMode, agentMode, styleConfig, themes,
       setResult, appendAiMessage, appendUserMessage, clearMessages,
       setLastMode, setAgentMode, setStyleConfig, setThemes,
       newWorkspace, hasWorkspace]);

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  return useContext(WorkspaceContext);
}
