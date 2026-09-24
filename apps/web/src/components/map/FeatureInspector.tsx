"use client";

import { Plane, Rocket, Satellite, Ship } from "lucide-react";
import { formatAge } from "@/components/layout/SourceStatusPanel";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { compassPoint, numberProp, shipCategory, stringProp } from "@/lib/telemetry";
import { useMapStore } from "@/store/mapStore";
import { useUiStore, type FollowTarget } from "@/store/uiStore";
import { CameraViewer } from "./CameraViewer";
import { TelemetryCard } from "./TelemetryCard";

const DASH = "—";

/** Details card for the clicked feature of an inspectable overlay */
export function FeatureInspector() {
  const { t, lang } = useTranslation();
  const inspected = useMapStore((s) => s.inspected);
  const setInspected = useMapStore((s) => s.setInspected);
  const follow = useUiStore((s) => s.follow);
  const setFollow = useUiStore((s) => s.setFollow);
  if (!inspected) return null;

  const close = () => {
    setInspected(null);
    setFollow(null);
  };
  /** Follow toggle for tracked objects that can be identified across refreshes */
  const followButton = (target: FollowTarget | null) => {
    if (!target) return undefined;
    const active = follow?.layerId === target.layerId && follow.value === target.value;
    return (
      <button
        type="button"
        onClick={() => setFollow(active ? null : target)}
        aria-pressed={active}
        className={`rounded px-2 py-0.5 text-[11px] ${active ? "bg-emerald-700 text-white" : "border border-gray-600 text-gray-300 hover:bg-gray-800"}`}
      >
        {active ? t.ops.following : t.ops.follow}
      </button>
    );
  };
  const p = inspected.properties;
  const number = new Intl.NumberFormat(lang, { maximumFractionDigits: 0 });
  const heading = (deg: number | null) => (deg === null ? DASH : `${number.format(deg)}° ${compassPoint(deg)}`);

  switch (inspected.layerId) {
    case "cameras": {
      const id = stringProp(p.id);
      if (!id) return null;
      return (
        <CameraViewer
          id={id}
          name={stringProp(p.name) ?? "Camera"}
          direction={stringProp(p.direction)}
          source={stringProp(p.source)}
          snapshotMinutes={numberProp(p.snapshot_minutes)}
          streamUrl={stringProp(p.stream_url)}
          onClose={close}
        />
      );
    }
    case "aircraft": {
      const altitude = numberProp(p.altitude_ft);
      const speed = numberProp(p.speed_kt);
      const seen = numberProp(p.seen_s);
      const military = p.military === true;
      return (
        <TelemetryCard
          icon={<Plane className={`h-4 w-4 ${military ? "text-orange-400" : "text-slate-200"}`} />}
          title={stringProp(p.callsign) ?? stringProp(p.hex) ?? DASH}
          subtitle={
            p.generalised === true
              ? t.telemetry.generalised
              : [stringProp(p.type), military ? t.telemetry.military : null].filter(Boolean).join(" · ") || undefined
          }
          rows={[
            {
              label: t.telemetry.altitude,
              value: p.on_ground === true ? t.telemetry.onGround : altitude === null ? DASH : `${number.format(altitude)} ft`,
            },
            { label: t.telemetry.speed, value: speed === null ? DASH : `${number.format(speed)} kt` },
            { label: t.telemetry.heading, value: heading(numberProp(p.track_deg)) },
            { label: t.telemetry.lastSeen, value: seen === null ? DASH : `${number.format(seen)} s` },
          ]}
          footer={
            <span className="flex items-center justify-between">
              ADS-B · adsb.lol
              {followButton(
                p.generalised === true || !stringProp(p.hex) ? null : { layerId: "aircraft", key: "hex", value: stringProp(p.hex)! },
              )}
            </span>
          }
          onClose={close}
        />
      );
    }
    case "vessels": {
      const category = shipCategory(numberProp(p.ship_type));
      const speed = numberProp(p.speed_kn);
      const updated = stringProp(p.updated_at);
      return (
        <TelemetryCard
          icon={<Ship className="h-4 w-4 text-teal-300" />}
          title={stringProp(p.name) ?? `MMSI ${numberProp(p.mmsi) ?? DASH}`}
          subtitle={p.generalised === true ? t.telemetry.generalised : category ? t.telemetry.shipTypes[category] : undefined}
          rows={[
            { label: t.telemetry.speed, value: speed === null ? DASH : `${speed.toFixed(1)} kn` },
            { label: t.telemetry.course, value: heading(numberProp(p.course_deg)) },
            { label: t.telemetry.heading, value: heading(numberProp(p.heading_deg)) },
            { label: t.telemetry.lastSeen, value: formatAge(updated, lang) ?? DASH },
          ]}
          footer={
            <span className="flex items-center justify-between">
              AIS · AISStream
              {followButton(
                p.generalised === true || numberProp(p.mmsi) === null
                  ? null
                  : { layerId: "vessels", key: "mmsi", value: numberProp(p.mmsi)! },
              )}
            </span>
          }
          onClose={close}
        />
      );
    }
    case "satellites": {
      const altitude = numberProp(p.altitude_km);
      return (
        <TelemetryCard
          icon={<Satellite className="h-4 w-4 text-sky-300" />}
          title={stringProp(p.name) ?? DASH}
          rows={[
            { label: "NORAD", value: numberProp(p.norad_id) ?? DASH },
            { label: t.telemetry.altitude, value: altitude === null ? DASH : `${number.format(altitude)} km` },
            {
              label: t.telemetry.position,
              value: `${inspected.lat.toFixed(2)}, ${inspected.lng.toFixed(2)}`,
            },
          ]}
          footer="SGP4 · CelesTrak"
          onClose={close}
        />
      );
    }
    case "launches": {
      const net = stringProp(p.net);
      const when = net
        ? `${new Intl.DateTimeFormat(lang, { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(net))} UTC`
        : DASH;
      return (
        <TelemetryCard
          icon={<Rocket className="h-4 w-4 text-pink-300" />}
          title={stringProp(p.name) ?? DASH}
          subtitle={net ? formatAge(net, lang) ?? undefined : undefined}
          rows={[
            { label: t.telemetry.launchTime, value: when },
            { label: t.telemetry.status, value: stringProp(p.status) ?? DASH },
            { label: t.telemetry.provider, value: stringProp(p.provider) ?? DASH },
            { label: t.telemetry.mission, value: stringProp(p.mission_type) ?? DASH },
            { label: t.telemetry.orbit, value: stringProp(p.orbit) ?? DASH },
            { label: t.telemetry.pad, value: stringProp(p.pad) ?? DASH },
          ]}
          footer="Launch Library 2 · The Space Devs"
          onClose={close}
        />
      );
    }
    default:
      return null;
  }
}
