"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

export default function NavBar() {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const isWorkspace = pathname === "/";
  const isHome = pathname.startsWith("/analytics");
  const isReports = pathname.startsWith("/reports");
  const isMemory = pathname.startsWith("/memory");
  const isAuthPage = pathname.startsWith("/login") || pathname.startsWith("/register");

  const linkCls = (active: boolean) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      active
        ? "bg-white/20 text-white"
        : "text-white/70 hover:text-white hover:bg-white/10"
    }`;

  return (
    <header className="sticky top-0 z-50 bg-gradient-to-r from-zinc-900 via-zinc-800 to-zinc-900 border-b border-zinc-700">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 h-12">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 text-white font-bold text-sm">
            <span className="w-6 h-6 rounded bg-blue-500 flex items-center justify-center text-[10px]">AI</span>
            AI Excel Agent
          </Link>
          {!isAuthPage && (
            <nav className="flex items-center gap-1">
              <Link href="/analytics" className={linkCls(isHome)}>Home</Link>
              <Link href="/" className={linkCls(isWorkspace)}>Workspace</Link>
              <Link href="/reports" className={linkCls(isReports)}>Reports</Link>
              <Link href="/memory" className={linkCls(isMemory)}>Memory</Link>
            </nav>
          )}
        </div>
        <div className="flex items-center gap-3">
          {loading ? (
            <span className="text-[10px] text-zinc-400">...</span>
          ) : user ? (
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-300">{user.username}</span>
              <button
                onClick={logout}
                className="text-[10px] text-zinc-400 hover:text-white transition-colors"
              >
                注销
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="text-xs text-zinc-300 hover:text-white transition-colors"
            >
              登录
            </Link>
          )}
          <span className="text-[10px] text-zinc-400">v2.1</span>
        </div>
      </div>
    </header>
  );
}
