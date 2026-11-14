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
