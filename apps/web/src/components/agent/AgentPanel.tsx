"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Loader2, Send, Sparkles, X } from "lucide-react";
import { applyMapActions, buildMapContext } from "@/lib/agent/actions";
import { agentAPI, APIError, type ApiDisasterEvent } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const SESSION_KEY = "phoenix:agent-session";
const HISTORY_SENT = 20;

interface Message {
  role: "user" | "assistant";
  content: string;
  /** Map actions applied for this reply */
  applied?: number;
  error?: boolean;
}

function sessionId(): string {
  try {
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) return saved;
    const created = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, created);
    return created;
  } catch {
    return crypto.randomUUID(); // storage blocked: a session per page load
  }
}

interface AgentPanelProps {
  onSelectEvent: (event: ApiDisasterEvent) => void;
}

/** Chat with the map assistant; its answers can move and filter the map */
export function AgentPanel({ onSelectEvent }: AgentPanelProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [usage, setUsage] = useState<{ used: number; cap: number } | null>(null);
  const session = useRef<string | null>(null);
  const listEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    agentAPI
      .status()
      .then((status) => setEnabled(status.enabled))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => {
    listEnd.current?.scrollIntoView({ block: "end" });
  }, [messages, busy]);

  const send = async (text: string) => {
    const content = text.trim();
    if (!content || busy) return;
    session.current ??= sessionId();
    const history: Message[] = [...messages.filter((m) => !m.error), { role: "user", content }];
    setMessages((current) => [...current, { role: "user", content }]);
    setDraft("");
    setBusy(true);
    try {
      const reply = await agentAPI.chat({
        session_id: session.current,
        messages: history.slice(-HISTORY_SENT).map(({ role, content: c }) => ({ role, content: c.slice(0, 4000) })),
        context: buildMapContext(),
      });
      const applied = await applyMapActions(reply.actions, { focusEvent: onSelectEvent, captions: t.brief.captions });
      setUsage({ used: reply.usage.sessionTokens, cap: reply.usage.sessionCap });
      setMessages((current) => [...current, { role: "assistant", content: reply.reply || "…", applied }]);
    } catch (error) {
      const message =
        error instanceof APIError && error.statusCode === 429
          ? error.message === "agent_budget_daily"
            ? t.agent.budgetDaily
            : t.agent.budgetSession
          : error instanceof APIError && error.statusCode === 503
            ? t.agent.disabled
            : t.agent.error;
      setMessages((current) => [...current, { role: "assistant", content: message, error: true }]);
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(draft);
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="pointer-events-auto flex items-center gap-2 rounded-full bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-lg hover:bg-primary-500"
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {t.agent.open}
      </button>
    );
  }

  const suggestions = [t.agent.suggestions.view, t.agent.suggestions.quakes, t.agent.suggestions.brief];
  return (
    <section
      aria-label={t.agent.title}
      className="pointer-events-auto flex h-[min(32rem,60vh)] w-[min(22rem,calc(100vw-2rem))] flex-col rounded-lg bg-gray-900/95 text-sm text-gray-200 shadow-xl backdrop-blur"
    >
      <header className="flex items-center gap-2 border-b border-gray-700/60 px-3 py-2">
        <Sparkles className="h-4 w-4 text-primary-400" aria-hidden="true" />
        <h2 className="flex-1 font-semibold text-white">{t.agent.title}</h2>
        <button type="button" onClick={() => setOpen(false)} className="rounded p-1 hover:bg-gray-800" aria-label={t.common.close}>
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </header>

      <div className="flex-1 space-y-2 overflow-y-auto px-3 py-2" aria-live="polite">
        {enabled === false && <p className="text-gray-400">{t.agent.disabled}</p>}
        {enabled && messages.length === 0 && (
          <div className="space-y-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => void send(suggestion)}
                className="block w-full rounded-md border border-gray-700 px-3 py-1.5 text-left text-gray-300 hover:bg-gray-800"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        {messages.map((message, i) => (
          <div key={i} className={message.role === "user" ? "flex justify-end" : ""}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-1.5 ${
                message.role === "user"
                  ? "bg-primary-700 text-white"
                  : message.error
                    ? "bg-red-900/40 text-red-200"
                    : "bg-gray-800 text-gray-200"
              }`}
            >
              {message.content}
              {!!message.applied && (
                <div className="mt-1 text-xs text-primary-300">
                  {t.agent.mapChanged.replace("{n}", String(message.applied))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            {t.agent.thinking}
          </div>
        )}
        <div ref={listEnd} />
      </div>

      {enabled && (
        <form onSubmit={onSubmit} className="border-t border-gray-700/60 p-2">
          <div className="flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              maxLength={4000}
              placeholder={t.agent.placeholder}
              aria-label={t.agent.placeholder}
              className="flex-1 rounded-md bg-gray-800 px-3 py-1.5 text-gray-100 placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <button
              type="submit"
              disabled={busy || !draft.trim()}
              className="rounded-md bg-primary-600 px-3 text-white hover:bg-primary-500 disabled:opacity-40"
              aria-label={t.agent.send}
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          {usage && (
            <div className="mt-1.5" title={t.agent.usage.replace("{used}", String(usage.used)).replace("{cap}", String(usage.cap))}>
              <div className="h-1 overflow-hidden rounded bg-gray-800">
                <div
                  className="h-full bg-primary-500"
                  style={{ width: `${Math.min(100, (usage.used / usage.cap) * 100)}%` }}
                />
              </div>
            </div>
          )}
        </form>
      )}
    </section>
  );
}
