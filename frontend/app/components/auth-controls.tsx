"use client";

import { useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? (
  process.env.NODE_ENV === "development" ? "http://localhost:8000" : ""
);

export function AuthControls() {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiUrl) {
      setLoading(false);
      setError("API URL is not configured.");
      return;
    }
    fetch(`${apiUrl}/auth/session`, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error("Session check failed");
        return response.json();
      })
      .then((body) => setAuthenticated(body.authenticated === true))
      .catch(() => {
        setAuthenticated(false);
        setError("Authentication service is unavailable.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <span className="text-sm text-slate-400">Checking session...</span>;
  }

  if (!apiUrl) {
    return <span className="text-sm text-amber-300">API URL is not configured</span>;
  }

  if (!authenticated) {
    return (
      <div className="flex items-center gap-3">
        {error && <span className="text-sm text-amber-300">{error}</span>}
        <a
          href={`${apiUrl}/auth/login`}
          className="rounded-xl border border-sky-400/40 bg-sky-400/10 px-4 py-2 text-sm text-sky-200"
        >
          Sign in
        </a>
      </div>
    );
  }

  return (
    <button
      type="button"
      className="rounded-xl border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-200"
      onClick={async () => {
        const csrf = document.cookie
          .split("; ")
          .find((part) => part.startsWith("personal_ai_os_csrf="))
          ?.split("=")[1];
        try {
          const response = await fetch(`${apiUrl}/auth/logout`, {
            method: "POST",
            credentials: "include",
            headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
          });
          if (!response.ok) throw new Error("Logout failed");
          setAuthenticated(false);
          setError(null);
        } catch {
          setError("Sign out failed. Please try again.");
        }
      }}
    >
      Sign out
    </button>
  );
}