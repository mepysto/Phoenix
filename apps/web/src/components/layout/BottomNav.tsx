"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { followWithFilters, isActiveItem, isGroup, primaryNav, type NavGroup } from "./nav";

const TAB =
  "flex flex-1 flex-col items-center justify-center gap-1 py-2 text-xs font-medium transition-colors";

/** The three ways to help, opened from the "Take part" tab */
function TakePartSheet({ group, onClose }: { group: NavGroup; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <button
        type="button"
        aria-label={group.label}
        tabIndex={-1}
        onClick={onClose}
        className="fixed inset-0 z-[55] bg-black/40"
      />
      <nav
        id="take-part-sheet"
        aria-label={group.label}
        className="fixed inset-x-0 bottom-[var(--bottom-nav-h)] z-[60] animate-panel-in rounded-t-2xl border-t border-gray-700 bg-gray-900 p-2 shadow-panel"
      >
        {group.items.map(({ href, label, hint, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            onClick={onClose}
            className="flex items-start gap-3 rounded-xl px-3 py-3 hover:bg-gray-800"
          >
            <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary-300" aria-hidden="true" />
            <span>
              <span className="block text-base font-medium text-white">{label}</span>
              {hint && <span className="block text-sm text-gray-400">{hint}</span>}
            </span>
          </Link>
        ))}
      </nav>
    </>
  );
}

/**
 * Phone and tablet navigation: four tabs fixed to the bottom of the screen
 * (UX plan 4.1). Its height is published as --bottom-nav-h (globals.css), so
 * full-height pages end above it.
 */
export function BottomNav() {
  const { t } = useTranslation();
  const pathname = usePathname();
  const router = useRouter();
  const [sheetOpen, setSheetOpen] = useState(false);
  useEffect(() => setSheetOpen(false), [pathname]);

  return (
    <>
      {sheetOpen &&
        primaryNav(t)
          .filter(isGroup)
          .map((group) => <TakePartSheet key={group.id} group={group} onClose={() => setSheetOpen(false)} />)}
      <nav
        id="bottom-nav"
        aria-label={t.common.menu}
        className="fixed inset-x-0 bottom-0 z-[60] flex h-[var(--bottom-nav-h)] items-stretch border-t border-gray-800 bg-gray-950 pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        {primaryNav(t).map((item) => {
          const active = isActiveItem(pathname, item) || (isGroup(item) && sheetOpen);
          const tone = active ? "text-white" : "text-gray-400 hover:text-white";
          const Icon = item.icon;
          const content = (
            <>
              <Icon className={`h-5 w-5 ${active ? "text-primary-300" : ""}`} aria-hidden="true" />
              {item.label}
            </>
          );
          return isGroup(item) ? (
            <button
              key={item.id}
              type="button"
              aria-expanded={sheetOpen}
              aria-controls="take-part-sheet"
              onClick={() => setSheetOpen((o) => !o)}
              className={`${TAB} ${tone}`}
            >
              {content}
            </button>
          ) : (
            <Link
              key={item.href}
              href={item.href}
              onClick={(e) => followWithFilters(e, item.href, pathname, router.push)}
              aria-current={active ? "page" : undefined}
              className={`${TAB} ${tone}`}
            >
              {content}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
