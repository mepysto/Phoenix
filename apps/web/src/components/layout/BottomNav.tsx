"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { followWithFilters, isActiveItem, primaryNav } from "./nav";

const TAB =
  "flex flex-1 flex-col items-center justify-center gap-1 py-2 text-xs font-medium transition-colors";

/**
 * Phone and tablet navigation: four tabs fixed to the bottom of the screen
 * (UX plan 4.1). Its height is published as --bottom-nav-h (globals.css), so
 * full-height pages end above it. "Take part" opens /act, which lists the
 * three ways to help.
 */
export function BottomNav() {
  const { t } = useTranslation();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <nav
      id="bottom-nav"
      aria-label={t.common.menu}
      className="fixed inset-x-0 bottom-0 z-[60] flex h-[var(--bottom-nav-h)] items-stretch border-t border-gray-800 bg-gray-950 pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      {primaryNav(t).map((item) => {
        const active = isActiveItem(pathname, item);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={(e) => followWithFilters(e, item.href, pathname, router.push)}
            aria-current={active ? "page" : undefined}
            className={`${TAB} ${active ? "text-white" : "text-gray-400 hover:text-white"}`}
          >
            <Icon className={`h-5 w-5 ${active ? "text-primary-300" : ""}`} aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
