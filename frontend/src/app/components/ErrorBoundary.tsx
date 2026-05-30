"use client";

import { Component, type ReactNode } from "react";

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; errorMessage: string }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message || "Unknown error" };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-4 m-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <p className="text-sm text-red-700 dark:text-red-400 font-medium">Something went wrong in this section.</p>
          <p className="text-xs text-red-500 mt-1">{this.state.errorMessage}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
