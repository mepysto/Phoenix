"use client";

import { EmptyState } from "@/components/ui/States";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Bell,
  BellOff,
  BellRing,
  LocateFixed,
  MapPin,
  Trash2,
  MapPinOff,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import type { SeverityLevel } from "@/lib/api/client";
import { RADIUS_CHOICES } from "@/lib/alerts";
import {
  pushState,
  syncAreas,
  turnOff,
  turnOn,
  type PushState,
} from "@/lib/push";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { newId } from "@/lib/sphere";
import { useAlertStore } from "@/store/alertStore";

const SEVERITIES: SeverityLevel[] = ["low", "medium", "high", "critical"];

type Perm = "default" | "granted" | "denied" | "unsupported";

function useNotificationPermission(): [Perm, () => Promise<void>] {
  const [perm, setPerm] = useState<Perm>("default");
  useEffect(() => {
    setPerm(
      typeof Notification === "undefined"
        ? "unsupported"
        : Notification.permission,
    );
  }, []);
  const ask = async () => {
    if (typeof Notification === "undefined") return;
    setPerm(await Notification.requestPermission());
  };
  return [perm, ask];
}

function AlertsContent() {
  const { t, lang } = useTranslation();
  const a = t.alerts;
  const params = useSearchParams();
  const { areas, recent, addArea, removeArea } = useAlertStore();
  const [perm, askPermission] = useNotificationPermission();
  const [push, setPush] = useState<PushState | "busy" | null>(null);
  const [pushError, setPushError] = useState(false);
  useEffect(() => {
    pushState()
      .then(setPush)
      .catch(() => setPush("unsupported"));
  }, []);
  // Keep the server's copy of the areas current while closed-tab alerts are on
  useEffect(() => {
    if (push === "on")
      void syncAreas(areas, lang).catch(() => setPushError(true));
    // Only when the areas change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [areas]);
  const togglePush = async () => {
    setPushError(false);
    const was = push;
    setPush("busy");
    try {
      setPush(was === "on" ? await turnOff() : await turnOn(areas, lang));
    } catch {
      setPushError(true);
      setPush(was);
    }
  };
  const [name, setName] = useState(params.get("name") ?? "");
  const [lat, setLat] = useState(params.get("lat") ?? "");
  const [lng, setLng] = useState(params.get("lng") ?? "");
  const [radiusKm, setRadiusKm] = useState<number>(250);
  const [minSeverity, setMinSeverity] = useState<SeverityLevel>("high");
  const [locating, setLocating] = useState<"idle" | "busy" | "denied">("idle");

  const locate = () => {
    if (!navigator.geolocation) return setLocating("denied");
    setLocating("busy");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        // Rounded: an area needs ~1 km precision, not the user's doorstep
        setLat(pos.coords.latitude.toFixed(2));
        setLng(pos.coords.longitude.toFixed(2));
        setLocating("idle");
      },
      () => setLocating("denied"),
      { maximumAge: 600_000, timeout: 10_000 },
    );
  };

  const latN = Number(lat);
  const lngN = Number(lng);
  const valid =
    name.trim().length > 0 &&
    lat !== "" &&
    lng !== "" &&
    Math.abs(latN) <= 90 &&
    Math.abs(lngN) <= 180;

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    addArea({
      id: newId(),
      name: name.trim(),
      lat: latN,
      lng: lngN,
      radiusKm,
      minSeverity,
      since: new Date().toISOString(),
    });
    setName("");
  };

  return (
    <main className="flex-1 px-4 py-8 md:px-8">
      <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1fr_22rem]">
        <section>
          <h1 className="text-3xl font-semibold tracking-tight text-white">
            {a.title}
          </h1>
          <p className="mt-2 max-w-xl text-gray-300">{a.intro}</p>
          <p className="mt-1 max-w-xl text-sm text-gray-400">{a.how}</p>

          <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-gray-800 bg-gray-900 px-4 py-3">
            {perm === "granted" ? (
              <BellRing
                className="h-5 w-5 text-primary-400"
                aria-hidden="true"
              />
            ) : (
              <BellOff className="h-5 w-5 text-gray-500" aria-hidden="true" />
            )}
            <span className="flex-1 text-sm text-gray-200">
              {a.notifications}:{" "}
              <span className="text-gray-400">
                {perm === "granted"
                  ? a.enabled
                  : perm === "denied"
                    ? a.blocked
                    : perm === "unsupported"
                      ? a.unsupported
                      : ""}
              </span>
            </span>
            {perm === "default" && (
              <button
                type="button"
                className="btn-primary py-1.5 text-xs"
                onClick={() => void askPermission()}
              >
                <Bell className="h-3.5 w-3.5" aria-hidden="true" />
                {a.enable}
              </button>
            )}
          </div>

          <section
            className="mt-3 rounded-xl border border-gray-800 bg-gray-900 px-4 py-3"
            aria-labelledby="push-title"
          >
            <div className="flex flex-wrap items-center gap-3">
              <h2
                id="push-title"
                className="flex-1 text-sm font-medium text-gray-100"
              >
                {t.push.title}
              </h2>
              {(push === "on" || push === "off" || push === "busy") && (
                <button
                  type="button"
                  className={
                    push === "on"
                      ? "btn-ghost py-1.5 text-xs"
                      : "btn-primary py-1.5 text-xs"
                  }
                  disabled={
                    push === "busy" || (push === "off" && areas.length === 0)
                  }
                  aria-pressed={push === "on"}
                  onClick={() => void togglePush()}
                >
                  {push === "on" ? t.push.off : t.push.on}
                </button>
              )}
            </div>
            <p className="mt-1 text-xs text-gray-400">
              {push === "on"
                ? t.push.isOn.replace("{n}", String(areas.length))
                : push === "unavailable"
                  ? t.push.unavailable
                  : push === "unsupported"
                    ? t.push.unsupported
                    : push === "blocked"
                      ? a.blocked
                      : areas.length === 0
                        ? t.push.needArea
                        : t.push.body}
            </p>
            {pushError && (
              <p role="alert" className="mt-1 text-xs text-ember-300">
                {t.push.failed}
              </p>
            )}
          </section>

          <h2 className="mt-8 text-sm font-semibold text-gray-300">
            {a.recent}
          </h2>
          {recent.length === 0 ? (
            <EmptyState
              className="mt-3"
              compact
              icon={BellOff}
              title={a.noRecent}
            />
          ) : (
            <ul className="mt-3 divide-y divide-gray-800 rounded-xl border border-gray-800 bg-gray-900">
              {recent.map((r) => (
                <li key={r.key} className="flex items-start gap-3 px-4 py-3">
                  <BellRing
                    className="mt-0.5 h-4 w-4 shrink-0 text-ember-400"
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/events/${r.eventId}`}
                      className="font-medium text-gray-100 hover:underline"
                    >
                      {r.title}
                    </Link>
                    <p className="text-xs text-gray-400">
                      {a.within
                        .replace("{km}", String(r.distanceKm))
                        .replace("{name}", r.areaName)}{" "}
                      ·{" "}
                      <time dateTime={r.at}>
                        {new Date(r.at).toLocaleString(lang)}
                      </time>
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="space-y-4">
          <h2 className="text-sm font-semibold text-gray-300">{a.areas}</h2>
          {areas.length === 0 ? (
            <EmptyState compact icon={MapPinOff} title={a.none} />
          ) : (
            <ul className="space-y-2">
              {areas.map((area) => (
                <li
                  key={area.id}
                  className="flex items-start justify-between gap-2 rounded-xl border border-gray-800 bg-gray-900 px-4 py-3"
                >
                  <div>
                    <p className="flex items-center gap-1.5 font-medium text-white">
                      <MapPin
                        className="h-4 w-4 text-primary-400"
                        aria-hidden="true"
                      />
                      {area.name}
                    </p>
                    <p className="mt-0.5 text-xs text-gray-400">
                      {area.radiusKm} km ·{" "}
                      {(t.sidebar as Record<string, string>)[area.minSeverity]}+
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeArea(area.id)}
                    aria-label={`${a.remove}: ${area.name}`}
                    title={a.remove}
                    className="rounded-md p-1.5 text-gray-400 hover:bg-gray-800 hover:text-ember-300"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <form
            onSubmit={save}
            className="space-y-3 rounded-xl border border-gray-800 bg-gray-900 p-5"
          >
            <h3 className="font-semibold text-white">{a.add}</h3>
            <div>
              <label htmlFor="area-name" className="field-label">
                {a.name}
              </label>
              <input
                id="area-name"
                required
                maxLength={60}
                className="field"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="area-lat" className="field-label">
                  {a.latitude}
                </label>
                <input
                  id="area-lat"
                  inputMode="decimal"
                  required
                  className="field"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="area-lng" className="field-label">
                  {a.longitude}
                </label>
                <input
                  id="area-lng"
                  inputMode="decimal"
                  required
                  className="field"
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                />
              </div>
            </div>
            <button
              type="button"
              onClick={locate}
              className="flex items-center gap-1.5 text-xs font-medium text-primary-300 hover:text-primary-200"
            >
              <LocateFixed className="h-3.5 w-3.5" aria-hidden="true" />
              {locating === "busy" ? a.locating : a.useMyLocation}
            </button>
            {locating === "denied" && (
              <p role="alert" className="text-xs text-ember-300">
                {a.locationDenied}
              </p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="area-radius" className="field-label">
                  {a.radius}
                </label>
                <select
                  id="area-radius"
                  className="field"
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                >
                  {RADIUS_CHOICES.map((r) => (
                    <option key={r} value={r}>
                      {r} km
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="area-sev" className="field-label">
                  {a.minSeverity}
                </label>
                <select
                  id="area-sev"
                  className="field"
                  value={minSeverity}
                  onChange={(e) =>
                    setMinSeverity(e.target.value as SeverityLevel)
                  }
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {(t.sidebar as Record<string, string>)[s]}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              type="submit"
              className="btn-primary w-full"
              disabled={!valid}
            >
              {a.save}
            </button>
          </form>
        </aside>
      </div>
    </main>
  );
}

export default function AlertsPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-950">
      <Header />
      <Suspense>
        <AlertsContent />
      </Suspense>
    </div>
  );
}
