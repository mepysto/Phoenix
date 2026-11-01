"use client";

import { useEffect } from "react";
import { SEVERITY_RANK, newAlerts } from "@/lib/alerts";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { useAlertStore } from "@/store/alertStore";
import { useEventStore } from "@/store/eventStore";

/**
 * Watch the live event store for disasters inside the user's areas and
 * raise a browser notification (when allowed) for each new one.
 */
export function useAreaAlerts(): void {
  const events = useEventStore((s) => s.events);
  const areas = useAlertStore((s) => s.areas);
  const seen = useAlertStore((s) => s.seen);
  const record = useAlertStore((s) => s.record);
  const { t } = useTranslation();

  useEffect(() => {
    if (areas.length === 0 || events.length === 0) return;
    const hits = newAlerts(events, areas, new Set(seen));
    if (hits.length === 0) return;
    const byId = new Map(events.map((e) => [e.id, e]));
    const areaById = new Map(areas.map((a) => [a.id, a]));
    const now = new Date().toISOString();
    const recorded = hits.map((h) => ({
      key: `${h.areaId}:${h.eventId}`,
      eventId: h.eventId,
      title: byId.get(h.eventId)?.title ?? "",
      areaName: areaById.get(h.areaId)?.name ?? "",
      distanceKm: Math.round(h.distanceKm),
      at: now,
    }));
    record(recorded);

    if (
      typeof Notification === "undefined" ||
      Notification.permission !== "granted"
    )
      return;
    // Most severe first; a burst of matches should not flood the screen
    const sorted = [...recorded].sort(
      (a, b) =>
        SEVERITY_RANK[
          (byId.get(b.eventId)?.severity ?? "low") as keyof typeof SEVERITY_RANK
        ] -
        SEVERITY_RANK[
          (byId.get(a.eventId)?.severity ?? "low") as keyof typeof SEVERITY_RANK
        ],
    );
    for (const r of sorted.slice(0, 3)) {
      const e = byId.get(r.eventId);
      if (!e) continue;
      const sev =
        (t.sidebar as Record<string, string>)[e.severity] ?? e.severity;
      const n = new Notification(
        t.alerts.notifTitle
          .replace("{severity}", sev)
          .replace("{title}", e.title),
        {
          body: t.alerts.within
            .replace("{km}", String(r.distanceKm))
            .replace("{name}", r.areaName),
          tag: r.key,
          icon: "/icon.svg",
        },
      );
      n.onclick = () => {
        window.focus();
        window.location.href = `/events/${e.id}`;
      };
    }
  }, [events, areas, seen, record, t]);
}
