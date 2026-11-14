"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Bell, ChevronDown, Search, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/store/authStore";
import { PhoenixMark } from "@/components/brand/PhoenixMark";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { AccountMenu } from "./AccountMenu";
import { BottomNav } from "./BottomNav";
import { Dropdown } from "./Dropdown";
import { followWithFilters, isActiveItem, isActivePath, isGroup, primaryNav, type NavGroup } from "./nav";

const NAV_LINK =
  "relative whitespace-nowrap py-1 text-sm font-medium transition-colors after:absolute after:inset-x-0 after:-bottom-[17px] after:h-0.5 after:rounded-full";
const navTone = (active: boolean) =>
  active ? "text-white after:bg-primary-400" : "text-gray-300 after:bg-transparent hover:text-white";

/** "Take part": the three ways to help, each with a one-line description */
function TakePartMenu({ group, active }: { group: NavGroup; active: boolean }) {
  const pathname = usePathname();
  return (
    <Dropdown
      align="start"
      triggerClassName={(open) => `${NAV_LINK} ${navTone(active || open)} flex items-center gap-1`}
      trigger={
        <>
          {group.label}
          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
        </>
      }
      panelClassName="w-80"
    >
      <ul>
        {group.items.map(({ href, label, hint, icon: Icon }) => (
          <li key={href}>
            <Link
              href={href}
              aria-current={isActivePath(pathname, href) ? "page" : undefined}
              className="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-gray-800 aria-[current=page]:bg-gray-800/70"
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary-300" aria-hidden="true" />
              <span>
                <span className="block text-sm font-medium text-white">{label}</span>
                {hint && <span className="block text-sm text-gray-400">{hint}</span>}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Dropdown>
  );
}

export function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const { status, refresh } = useAuthStore();
  const { t } = useTranslation();
  const nav = primaryNav(t);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    if (status === "unknown") void refresh();
  }, [status, refresh]);

  useEffect(() => setSearchOpen(false), [pathname]);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (searchQuery.trim()) {
        router.push(`/events?q=${encodeURIComponent(searchQuery.trim())}`);
        setSearchOpen(false);
      }
    },
    [searchQuery, router],
  );

  const searchField = (id: string, autoFocus = false) => (
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
        // Opened on purpose by the search button, so focus follows
        autoFocus={autoFocus}
        placeholder={t.common.searchPlaceholder}
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="w-full rounded-full border border-gray-700 bg-gray-900 py-2 pe-4 ps-10 text-sm text-white placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
      />
    </div>
  );

  const iconButton =
    "rounded-lg p-2 text-gray-300 transition-colors hover:bg-gray-800 hover:text-white";

  return (
    <>
      <header className="sticky top-0 z-50 flex h-14 items-center gap-3 border-b border-gray-800 bg-gray-950 px-4">
        <Link href="/" className="flex shrink-0 items-center gap-2 text-gray-100">
          <PhoenixMark className="h-7 w-7" />
          <span className="text-lg font-semibold tracking-tight text-white">Phoenix</span>
        </Link>

        <nav aria-label={t.common.menu} className="ms-4 hidden shrink-0 items-center gap-6 lg:flex">
          {nav.map((item) => {
            const active = isActiveItem(pathname, item);
            return isGroup(item) ? (
              <TakePartMenu key={item.id} group={item} active={active} />
            ) : (
              <Link
                key={item.href}
                href={item.href}
                onClick={(e) => followWithFilters(e, item.href, pathname, router.push)}
                aria-current={active ? "page" : undefined}
                className={`${NAV_LINK} ${navTone(active)}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <form
          onSubmit={handleSearch}
          role="search"
          className="ms-auto hidden min-w-0 max-w-sm flex-1 md:flex"
        >
          {searchField("global-search")}
        </form>

        <div className="ms-auto flex shrink-0 items-center gap-1 md:ms-2">
          <button
            type="button"
            onClick={() => setSearchOpen((o) => !o)}
            aria-label={t.common.search}
            aria-expanded={searchOpen}
            aria-controls="mobile-search"
            className={`${iconButton} md:hidden`}
          >
            {searchOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Search className="h-5 w-5" aria-hidden="true" />}
          </button>
          <Link
            href="/alerts"
            aria-label={t.alerts.title}
            title={t.alerts.title}
            aria-current={isActivePath(pathname, "/alerts") ? "page" : undefined}
            className={`${iconButton} ${isActivePath(pathname, "/alerts") ? "text-white" : ""}`}
          >
            <Bell className="h-5 w-5" aria-hidden="true" />
          </Link>
          <AccountMenu />
        </div>
      </header>

      {searchOpen && (
        <form
          id="mobile-search"
          onSubmit={handleSearch}
          role="search"
          className="sticky top-14 z-50 border-b border-gray-800 bg-gray-950 p-3 md:hidden"
        >
          {searchField("mobile-search-input", true)}
        </form>
      )}

      <BottomNav />
    </>
  );
}
