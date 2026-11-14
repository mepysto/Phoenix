"use client";

import dynamic from "next/dynamic";
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
import { DisasterPick } from "@/components/alerts/DisasterPick";
import { PlaceSearch } from "@/components/ui/PlaceSearch";

// Map in a dynamic import: MapLibre needs the browser
const AreaPickerMap = dynamic(() => import("@/components/alerts/AreaPickerMap"), {
  ssr: false,
  loading: () => <div className="h-56 animate-pulse rounded-lg bg-gray-800" />,
});
import { formatMoment } from "@/lib/format";
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

          {/* One place for both ways of being told, each saying what it does (UX plan 5.4) */}
          <section
            aria-labelledby="notify-title"
            className="mt-6 divide-y divide-gray-800 rounded-xl border border-gray-700/80 bg-gray-900"
          >
            <h2 id="notify-title" className="px-4 pb-2 pt-3 text-sm font-semibold text-gray-100">
              {t.ux.notifyTitle}
            </h2>
            <div className="flex flex-wrap items-start gap-3 px-4 py-3">
              {perm === "granted" ? (
                <BellRing className="mt-0.5 h-5 w-5 shrink-0 text-primary-400" aria-hidden="true" />
              ) : (
                <BellOff className="mt-0.5 h-5 w-5 shrink-0 text-gray-500" aria-hidden="true" />
              )}
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-medium text-gray-100">{t.ux.notifyOpenTitle}</h3>
                <p className="mt-0.5 text-sm text-gray-400">
                  {perm === "denied" ? a.blocked : perm === "unsupported" ? a.unsupported : t.ux.notifyOpenBody}
                </p>
              </div>
              {perm === "granted" && (
                <span className="rounded-full bg-primary-400/15 px-2.5 py-1 text-sm font-medium text-primary-200">
                  {t.ux.notifyOn}
                </span>
              )}
              {perm === "default" && (
                <button type="button" className="btn-primary py-1.5" onClick={() => void askPermission()}>
                  <Bell className="h-4 w-4" aria-hidden="true" />
                  {t.push.on}
                </button>
              )}
            </div>
            <div className="flex flex-wrap items-start gap-3 px-4 py-3">
              <BellRing
                className={`mt-0.5 h-5 w-5 shrink-0 ${push === "on" ? "text-primary-400" : "text-gray-500"}`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <h3 id="push-title" className="text-sm font-medium text-gray-100">
                  {t.ux.notifyClosedTitle}
                </h3>
                <p className="mt-0.5 text-sm text-gray-400">
                  {push === "on"
                    ? t.push.isOn.replace("{n}", String(areas.length))
                    : push === "unavailable"
                      ? t.push.unavailable
                      : push === "unsupported"
                        ? t.push.unsupported
                        : push === "blocked"
                          ? a.blocked
                          : areas.length === 0
                            ? `${t.push.body} ${t.push.needArea}`
                            : t.push.body}
                </p>
                {pushError && (
                  <p role="alert" className="mt-1 text-sm text-ember-300">
                    {t.push.failed}
                  </p>
                )}
              </div>
              {(push === "on" || push === "off" || push === "busy") && (
                <button
                  type="button"
                  role="switch"
                  aria-checked={push === "on"}
                  aria-labelledby="push-title"
                  disabled={push === "busy" || (push === "off" && areas.length === 0)}
                  onClick={() => void togglePush()}
                  className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                    push === "on" ? "bg-primary-500" : "bg-gray-700"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-[inset-inline-start] ${
                      push === "on" ? "start-[1.375rem]" : "start-0.5"
                    }`}
                  />
                </button>
              )}
            </div>
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
            <ul className="mt-3 divide-y divide-gray-800 rounded-xl border border-gray-700/80 bg-gray-900">
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
                        {formatMoment(r.at, lang)}
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
                  className="flex items-start justify-between gap-2 rounded-xl border border-gray-700/80 bg-gray-900 px-4 py-3"
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
            className="space-y-3 rounded-xl border border-gray-700/80 bg-gray-900 p-5"
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
            {/* Choose the place without typing numbers (UX plan A-05): by name, on the map, or nearby */}
            <PlaceSearch
              onPick={(place) => {
                setLat(place.lat.toFixed(2));
                setLng(place.lng.toFixed(2));
                if (!name.trim()) setName(place.name);
              }}
            />
            <div>
              <p className="field-label">{t.ux.alertsPickOnMap}</p>
              <AreaPickerMap
                lat={lat !== "" && Number.isFinite(latN) ? latN : null}
                lng={lng !== "" && Number.isFinite(lngN) ? lngN : null}
                radiusKm={radiusKm}
                label={t.ux.alertsPickOnMap}
                onPick={(la, lo) => {
                  setLat(String(la));
                  setLng(String(lo));
                }}
              />
              <p className="mt-1.5 text-sm text-gray-300" aria-live="polite">
                {lat !== "" && lng !== ""
                  ? t.ux.alertsCentre.replace("{lat}", lat).replace("{lng}", lng)
                  : t.ux.alertsPickFirst}
              </p>
            </div>
            <button
              type="button"
              onClick={locate}
              className="flex items-center gap-1.5 text-sm font-medium text-primary-300 hover:text-primary-200"
            >
              <LocateFixed className="h-4 w-4" aria-hidden="true" />
              {locating === "busy" ? a.locating : a.useMyLocation}
            </button>
            <DisasterPick
              onPick={(place, la, lo) => {
                setLat(String(la));
                setLng(String(lo));
                if (!name.trim()) setName(place);
              }}
            />
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-gray-300 hover:text-white">
                {t.ux.alertsEnterCoords}
              </summary>
              <div className="mt-2 grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="area-lat" className="field-label">
                    {a.latitude}
                  </label>
                  <input
                    id="area-lat"
                    inputMode="decimal"
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
                    className="field"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                  />
                </div>
              </div>
            </details>
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
