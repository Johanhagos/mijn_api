"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import api from "../lib/api";

export default function Header() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [name, setName] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    try {
      const e = localStorage.getItem("merchant_email");
      setEmail(e);
      const n = localStorage.getItem("merchant_name");
      setName(n);
    } catch (err) {
      // ignore
    }

    let mounted = true;
    (async () => {
      try {
        const info = await api.protectedApi("/merchant/me");
        if (!mounted) return;
        setName(
          info?.name || info?.merchant_name || info?.display_name || "Merchant"
        );
        setEmail(
          info?.email || info?.merchant_email || info?.contact_email || null
        );
      } catch {
        try {
          const usage = await api.protectedApi("/merchant/usage");
          if (!mounted) return;
          setName(usage?.merchant_name || usage?.merchant || "Merchant");
          setEmail(usage?.merchant_email || usage?.email || null);
        } catch {
          // ignore
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  function logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem("token");
      localStorage.removeItem("jwt");
      localStorage.removeItem("merchant_id");
      localStorage.removeItem("merchant_name");
      localStorage.removeItem("merchant_email");
      window.location.href = "/login";
    } else {
      router.push("/login");
    }
  }

  if (!mounted) {
    return (
      <header className="h-16" style={{ background: 'var(--ab-surface)' }} />
    );
  }

  return (
    <header className="flex justify-between items-center p-4 border-b shadow-sm" style={{ background: '#FFFFFF' }}>
      <div className="flex items-center gap-4">
        <div className="h-10 w-10 flex items-center justify-center rounded bg-gradient-to-br from-primary to-secondary text-white font-extrabold tracking-tight">
          <span className="text-sm">APIBl</span>
        </div>
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Dashboard — Invoicing Merchant</h1>
          {email ? <p className="text-sm text-slate-600">{email}</p> : null}
        </div>
      </div>

      <button
        onClick={logout}
        className="ml-auto btn btn-ghost"
      >
        Logout
      </button>
    </header>
  );
}
