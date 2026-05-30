"use client";

import { ReactNode } from "react";
import { AuthProvider } from "@/lib/AuthContext";
import { WorkspaceProvider } from "@/lib/WorkspaceContext";
import NavBar from "./NavBar";

export default function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        <NavBar />
        {children}
      </WorkspaceProvider>
    </AuthProvider>
  );
}
