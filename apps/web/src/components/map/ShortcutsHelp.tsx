"use client";

import { X } from "lucide-react";
import { SHORTCUTS } from "@/hooks/useKeyboardShortcuts";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useUiStore } from "@/store/uiStore";

const KEY_LABEL: Record<string, string> = { Escape: "Esc" };

/** Keyboard shortcut list, opened with "?" */
export function ShortcutsHelp() {
  const { t } = useTranslation();
  const open = useUiStore((s) => s.shortcutsOpen);
  const setOpen = useUiStore((s) => s.setShortcutsOpen);
  if (!open) return null;
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setOpen(false)}>
      <section
        role="dialog"
        aria-modal="true"
        aria-label={t.ops.shortcuts}
        onClick={(e) => e.stopPropagation()}
        className="w-80 rounded-lg bg-gray-900 p-4 text-sm text-gray-200 shadow-2xl"
      >
        <header className="mb-3 flex items-center">
          <h2 className="flex-1 font-semibold text-white">{t.ops.shortcuts}</h2>
          <button type="button" onClick={() => setOpen(false)} className="rounded p-1 hover:bg-gray-800" aria-label={t.common.close}>
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </header>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
          {SHORTCUTS.map((key) => (
            <div key={key} className="contents">
              <dt>
                <kbd className="rounded border border-gray-600 bg-gray-800 px-1.5 py-0.5 font-mono text-xs">
                  {KEY_LABEL[key] ?? key.toUpperCase()}
                </kbd>
              </dt>
              <dd className="text-gray-300">{t.ops.keys[key]}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
