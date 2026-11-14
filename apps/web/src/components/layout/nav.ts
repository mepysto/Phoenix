import {
  BarChart3,
  HandHeart,
  LayoutGrid,
  List,
  Map as MapIcon,
  Trophy,
  type LucideIcon,
} from "lucide-react";
import type { Translations } from "@/lib/i18n/types";
import { sharedFilterQuery } from "@/lib/eventQuery";

/**
 * Site navigation (docs/UX_REDESIGN_PLAN.md 4.1): four top-level items,
 * with the three ways to help grouped under "Take part". URLs are unchanged.
 */
export interface NavLink {
  href: string;
  label: string;
  icon: LucideIcon;
  hint?: string;
}

export interface NavGroup {
  id: "take-part";
  label: string;
  icon: LucideIcon;
  items: NavLink[];
}

export type NavItem = NavLink | NavGroup;

export const isGroup = (item: NavItem): item is NavGroup => "items" in item;

export function takePartLinks(t: Translations): NavLink[] {
  return [
    { href: "/connect", label: t.ux.navNeeds, hint: t.ux.navNeedsHint, icon: HandHeart },
    { href: "/plan", label: t.ux.navPlan, hint: t.ux.navPlanHint, icon: LayoutGrid },
    { href: "/challenges", label: t.ux.navChallenges, hint: t.ux.navChallengesHint, icon: Trophy },
  ];
}

export function primaryNav(t: Translations): NavItem[] {
  return [
    { href: "/", label: t.ux.navMap, icon: MapIcon },
    { href: "/events", label: t.ux.navDisasters, icon: List },
    { id: "take-part", label: t.ux.navTakePart, icon: HandHeart, items: takePartLinks(t) },
    { href: "/dashboard", label: t.dashboard.nav, icon: BarChart3 },
  ];
}

export function isActivePath(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
}

export function isActiveItem(pathname: string | null, item: NavItem): boolean {
  return isGroup(item)
    ? item.items.some((link) => isActivePath(pathname, link.href))
    : isActivePath(pathname, item.href);
}

/** Pages that share event filters in the URL (UX plan 4.2) */
const FILTER_PAGES = ["/", "/events"];

/** Where a nav link should go: between the map and the list, the filters come along */
export function withSharedFilters(href: string, pathname: string | null, search: string): string {
  if (!FILTER_PAGES.includes(href) || !FILTER_PAGES.includes(pathname ?? "")) return href;
  const qs = sharedFilterQuery(search);
  return qs ? `${href}?${qs}` : href;
}

/** onClick for a nav <Link>: follow with the current filters when they apply */
export function followWithFilters(
  e: React.MouseEvent<HTMLAnchorElement>,
  href: string,
  pathname: string | null,
  push: (url: string) => void,
): void {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // new tab etc.
  const to = withSharedFilters(href, pathname, window.location.search);
  if (to === href) return;
  e.preventDefault();
  push(to);
}
