"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { getToken, setToken, clearToken } from "./api";
import { API_BASE } from "./config";

interface User {
  id: number;
  username: string;
  email: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = getToken();
    if (!savedToken) {
      setLoading(false);
      return;
    }
    setTokenState(savedToken);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);

    fetch(`${API_BASE}/me`, {
      headers: { Authorization: `Bearer ${savedToken}` },
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error("invalid token");
        return r.json();
      })
      .then((data) => {
        if (data.id) setUser(data);
      })
      .catch(() => {
        clearToken();
        setTokenState(null);
      })
      .finally(() => {
        clearTimeout(timer);
        setLoading(false);
      });
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setTokenState(newToken);
    setUser(newUser);
  };

  const logout = () => {
    clearToken();
    setTokenState(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
