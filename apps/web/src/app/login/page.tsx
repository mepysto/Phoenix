"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { MailCheck } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { PhoenixMark } from "@/components/brand/PhoenixMark";
import { authAPI } from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";

function LoginForm() {
  const { t } = useTranslation();
  const next = useSearchParams().get("next") ?? "/connect";
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [devLink, setDevLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setState("sending");
    setError(null);
    try {
      const r = await authAPI.requestLink(email, next);
      setDevLink(r.devLink);
      setState("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setState("idle");
    }
  };

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm">
        <PhoenixMark className="mb-6 h-12 w-12 text-gray-200" />
        {state === "sent" ? (
          <div role="status">
            <MailCheck
              className="mb-3 h-6 w-6 text-primary-400"
              aria-hidden="true"
            />
            <h1 className="text-2xl font-semibold text-white">{t.auth.sent}</h1>
            <p className="mt-2 text-gray-300">
              {t.auth.sentBody.replace("{email}", email)}
            </p>
            {devLink && (
              <a href={devLink} className="btn-ghost mt-6 w-full">
                {t.auth.devLink}
              </a>
            )}
          </div>
        ) : (
          <form onSubmit={submit}>
            <h1 className="text-2xl font-semibold text-white">
              {t.auth.title}
            </h1>
            <p className="mt-2 text-gray-300">{t.auth.body}</p>
            <label htmlFor="email" className="field-label mt-6">
              {t.auth.email}
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field"
            />
            {error && (
              <p role="alert" className="mt-2 text-sm text-ember-300">
                {error}
              </p>
            )}
            <button
              type="submit"
              className="btn-primary mt-4 w-full py-2.5"
              disabled={state === "sending"}
            >
              {state === "sending" ? t.auth.sending : t.auth.send}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
