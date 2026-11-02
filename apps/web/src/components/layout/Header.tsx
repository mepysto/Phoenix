"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  Languages,
  LogOut,
  Menu,
  Search,
  Settings,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";
import {
  LANGUAGE_LABELS,
  useSettingsStore,
  type Language,
} from "@/store/settingsStore";
import { PhoenixMark } from "@/components/brand/PhoenixMark";
import { useTranslation } from "@/lib/i18n/useTranslation";

function useNav() {
  const { t } = useTranslation();
  return [
    { href: "/", label: t.common.home },
    { href: "/events", label: t.common.events },
    { href: "/connect", label: t.connect.nav },
    { href: "/plan", label: t.ux.plan },
    { href: "/challenges", label: t.challenges.nav },
    { href: "/about", label: t.common.about },
  ];
}

/** Compact language picker: the interface serves seven languages, so it lives in the chrome */
function LanguagePicker({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  const language = useSettingsStore((s) => s.language);
  const setLanguage = useSettingsStore((s) => s.setLanguage);
  return (
    <label
      className={`relative flex items-center rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white ${className}`}
      title={t.ux.language}
    >
      <Languages
        className="pointer-events-none absolute start-2 h-4 w-4"
        aria-hidden="true"
      />
      <span className="sr-only">{t.ux.language}</span>
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value as Language)}
        className="cursor-pointer appearance-none bg-transparent py-2 pe-2 ps-8 text-xs font-medium text-inherit focus:outline-none"
      >
        {(Object.keys(LANGUAGE_LABELS) as Language[]).map((code) => (
          <option key={code} value={code}>
            {LANGUAGE_LABELS[code]}
          </option>
        ))}
      </select>
    </label>
  );
}

export function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const { me, status, refresh, logout } = useAuthStore();
  const { t } = useTranslation();
  const nav = useNav();
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  // Close the menu on navigation and on Escape
  useEffect(() => setMobileMenuOpen(false), [pathname]);
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileMenuOpen]);

  const isActive = (href: string) =>
    pathname === href || (href !== "/" && !!pathname?.startsWith(href));

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (searchQuery.trim()) {
        router.push(`/events?q=${encodeURIComponent(searchQuery.trim())}`);
        setMobileMenuOpen(false);
      }
    },
    [searchQuery, router],
  );

  const searchField = (id: string) => (
    <div className="relative w-full">
      <Search
        className="pointer-events-none absolute start-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
        aria-hidden="true"
      />
      <label htmlFor={id} className="sr-only">
        {t.common.search}
      </label>
      <input
        id={id}
        type="search"
        placeholder={t.common.searchPlaceholder}
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full rounded-full border border-gray-700 bg-gray-900 py-2 pe-4 ps-10 text-sm text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      />
    </div>
  );

  const iconLink =
    "rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white";

  return (
    <>
      <header className="sticky top-0 z-50 flex h-14 items-center gap-3 border-b border-gray-800 bg-gray-950 px-4">
        <button
          type="button"
          className="-ms-1 rounded-lg p-2 text-gray-300 hover:bg-gray-800 lg:hidden"
          onClick={() => setMobileMenuOpen((o) => !o)}
          aria-label={t.common.menu}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-menu"
        >
          {mobileMenuOpen ? (
            <X className="h-5 w-5" aria-hidden="true" />
          ) : (
            <Menu className="h-5 w-5" aria-hidden="true" />
          )}
        </button>
        <Link href="/" className="flex shrink-0 items-center gap-2 text-gray-100">
          <PhoenixMark className="h-7 w-7" />
          <span className="text-lg font-semibold tracking-tight text-white">
            Phoenix
          </span>
        </Link>

        <form
          onSubmit={handleSearch}
          role="search"
          className="mx-auto hidden min-w-0 max-w-md flex-1 md:flex lg:mx-6"
        >
          {searchField("global-search")}
        </form>

        <nav
          aria-label={t.common.menu}
          className="hidden shrink-0 items-center gap-5 lg:flex"
        >
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive(item.href) ? "page" : undefined}
              className={`relative whitespace-nowrap py-1 text-sm transition-colors after:absolute after:inset-x-0 after:-bottom-[17px] after:h-0.5 after:rounded-full ${
                isActive(item.href)
                  ? "text-white after:bg-primary-400"
                  : "text-gray-400 after:bg-transparent hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ms-auto flex shrink-0 items-center gap-1 lg:ms-2">
          <LanguagePicker className="hidden sm:flex" />
          <Link
            href="/alerts"
            aria-label={t.alerts.title}
            title={t.alerts.title}
            aria-current={isActive("/alerts") ? "page" : undefined}
            className={`${iconLink} ${isActive("/alerts") ? "text-white" : ""}`}
          >
            <Bell className="h-5 w-5" aria-hidden="true" />
          </Link>
          {status === "signed-in" && me ? (
            <>
              <Link
                href="/connect/mine"
                title={me.email}
                aria-label={`${t.auth.account}: ${me.email}`}
                className="mx-1 flex h-8 w-8 items-center justify-center rounded-full bg-primary-400/20 text-sm font-semibold uppercase text-primary-100 ring-1 ring-primary-400/40 hover:bg-primary-400/30"
              >
                {me.email.charAt(0)}
              </Link>
              <button
                type="button"
                onClick={() => void logout()}
                aria-label={t.auth.signOut}
                title={t.auth.signOut}
                className={`${iconLink} hidden sm:inline-flex`}
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
              </button>
            </>
          ) : status === "signed-out" ? (
            <Link
              href="/login"
              className="mx-1 hidden whitespace-nowrap rounded-full border border-gray-700 px-3 py-1.5 text-sm font-medium text-gray-100 hover:bg-gray-800 sm:inline-flex"
            >
              {t.auth.signIn}
            </Link>
          ) : null}
          <Link
            href="/settings"
            aria-label={t.common.settings}
            title={t.common.settings}
            aria-current={isActive("/settings") ? "page" : undefined}
            className={iconLink}
          >
            <Settings className="h-5 w-5" aria-hidden="true" />
          </Link>
        </div>
      </header>

      {mobileMenuOpen && (
        <div
          id="mobile-menu"
          className="fixed inset-x-0 top-14 z-[60] max-h-[calc(100dvh-3.5rem)] animate-panel-in overflow-y-auto border-b border-gray-800 bg-gray-900 shadow-panel lg:hidden"
        >
          <form onSubmit={handleSearch} role="search" className="p-4 md:hidden">
            {searchField("mobile-search")}
          </form>
          <nav aria-label={t.common.menu} className="flex flex-col pb-2">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive(item.href) ? "page" : undefined}
                className={`border-s-2 px-4 py-3 transition-colors ${
                  isActive(item.href)
                    ? "border-primary-400 bg-gray-800/60 font-medium text-white"
                    : "border-transparent text-gray-300 hover:bg-gray-800 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center justify-between gap-2 border-t border-gray-800 px-4 py-3">
            {status === "signed-in" && me ? (
              <button
                type="button"
                onClick={() => void logout()}
                className="btn-ghost"
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                {t.auth.signOut}
              </button>
            ) : (
              <Link href="/login" className="btn-primary">
                {t.auth.signIn}
              </Link>
            )}
            <LanguagePicker />
          </div>
        </div>
      )}
    </>
  );
}
