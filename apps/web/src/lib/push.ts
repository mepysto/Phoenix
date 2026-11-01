/**
 * Closed-tab alerts: subscribe this browser to Web Push with its watch
 * areas. Opt-in; turning it off deletes the areas from the server.
 */

import { API_URL } from "@/lib/api/client";
import type { WatchArea } from "@/lib/alerts";

export type PushState =
  "unsupported" | "unavailable" | "off" | "on" | "blocked";

function keyBytes(b64u: string): ArrayBuffer {
  const pad = "=".repeat((4 - (b64u.length % 4)) % 4);
  const raw = atob((b64u + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out.buffer;
}

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

async function registration(): Promise<ServiceWorkerRegistration> {
  return (
    (await navigator.serviceWorker.getRegistration()) ??
    navigator.serviceWorker.register("/sw.js")
  );
}

export async function pushState(): Promise<PushState> {
  if (!pushSupported()) return "unsupported";
  if (Notification.permission === "denied") return "blocked";
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  return sub ? "on" : "off";
}

function areasBody(areas: WatchArea[]) {
  return areas.slice(0, 10).map((a) => ({
    name: a.name.slice(0, 60),
    lat: a.lat,
    lng: a.lng,
    radius_km: a.radiusKm,
    min_severity: a.minSeverity,
  }));
}

async function send(
  sub: PushSubscription,
  areas: WatchArea[],
  lang: string,
): Promise<void> {
  const json = sub.toJSON() as {
    endpoint: string;
    keys: { p256dh: string; auth: string };
  };
  const r = await fetch(`${API_URL}/api/v1/push/subscription`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      endpoint: json.endpoint,
      keys: json.keys,
      areas: areasBody(areas),
      lang,
    }),
  });
  if (!r.ok) throw new Error(`Subscription failed (${r.status})`);
}

/** Returns the new state; "unavailable" when the server has no push keys. */
export async function turnOn(
  areas: WatchArea[],
  lang: string,
): Promise<PushState> {
  if (!pushSupported()) return "unsupported";
  const keyRes = await fetch(`${API_URL}/api/v1/push/vapid-public-key`);
  if (keyRes.status === 503) return "unavailable";
  if (!keyRes.ok) throw new Error(`Push key unavailable (${keyRes.status})`);
  const { public_key } = (await keyRes.json()) as { public_key: string };
  if ((await Notification.requestPermission()) !== "granted") return "blocked";
  const reg = await registration();
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBytes(public_key),
    }));
  await send(sub, areas, lang);
  return "on";
}

/** Keep the server's copy of the areas in step with this browser's. */
export async function syncAreas(
  areas: WatchArea[],
  lang: string,
): Promise<void> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (!sub) return;
  if (areas.length === 0) await turnOff();
  else await send(sub, areas, lang);
}

export async function turnOff(): Promise<PushState> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (sub) {
    await fetch(`${API_URL}/api/v1/push/unsubscribe`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ endpoint: sub.endpoint }),
    }).catch(() => undefined);
    await sub.unsubscribe();
  }
  return "off";
}
