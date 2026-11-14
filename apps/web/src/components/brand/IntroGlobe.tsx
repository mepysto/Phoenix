"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { SEVERITY_COLORS } from "@phoenix/shared/constants";
import type { ApiDisasterEvent, SeverityLevel } from "@/lib/api/client";
import { getEventPosition } from "@/lib/eventPosition";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { PhoenixMark } from "./PhoenixMark";

const SEEN_KEY = "phoenix:intro-seen";
// The intro steps aside on its own after this long (UX plan G-04)
const AUTO_CLOSE_MS = 3000;
const TILT = (23.4 * Math.PI) / 180;
const DOTS = 2400;
// Which lattice points fall on land (Natural Earth 1:110m via world-atlas),
// one bit per point in lattice order. Generated offline; 300 bytes instead
// of shipping coastlines.
const LAND_BITS =
  "AASEhIABMHdk7r3dv732dt7eytj5Oy13J+TnzJyen1Nzc25Oz8mpuTk3o+bkxIyakxFzak5MzqgJORUjpmbEhIyaEVMyakJMyakpOSUlpuSUlIyCUlJwSkpFSSkpMCWlpILUFBqSUlNASAoFAakpIASFgIAQFBICUkBBKCoJASmhIASUhIIQUBACClJBASgIRAWoKAAVgKICUFCICkBRESggBAWgoBgUkIIiUEQICkhBASggBEWgoAAUgYICUEQAikJBESgqAEWgiAgchaIiUASEikARECgCQkSgCAgUASIgUASEiEARECgABECAAAgAAAIhQAAIAAABEAAABAAAABAIAAAAAAAIAAAAAAAABAAAAAAAAAAAAAAAAAAAAABCREgJKT2l5/W8n9//";
const ORBIT_TILT = -0.35;

function landMask(): Uint8Array {
  const raw = atob(LAND_BITS);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

interface IntroGlobeProps {
  events: ApiDisasterEvent[];
}

interface Pt {
  lat: number;
  lng: number;
  color: string;
  size: number;
}

const SEVERITY_SIZE: Record<string, number> = {
  low: 2.6,
  medium: 3.2,
  high: 4,
  critical: 5,
};

// Once per device, not per tab session: returning visitors go straight to the map
function readSeen(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

function writeSeen() {
  try {
    localStorage.setItem(SEEN_KEY, "1");
  } catch {
    // Private mode: the intro will just show again next visit
  }
}

/** A shared link (event, view, filters) should open on what it points at */
function arrivedWithMapState(): boolean {
  return window.location.search.length > 1;
}

/** Evenly spread points on a sphere (Fibonacci lattice), as lat/lng radians */
function lattice(n: number): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    out.push([Math.asin(y), (i * golden) % (2 * Math.PI)]);
  }
  return out;
}

/**
 * First-visit intro: a dot globe turning on its axis, with every live event
 * glowing at its real position. Opening the map dives into the globe.
 * Shown once per device and closes itself after a few seconds; skipped for
 * links that carry map state; static when the viewer prefers less motion.
 */
export function IntroGlobe({ events }: IntroGlobeProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const pointsRef = useRef<Pt[]>([]);

  useEffect(() => {
    // Decided after mount so server and client render the same markup
    if (!readSeen() && !arrivedWithMapState()) setOpen(true);
  }, []);

  useEffect(() => {
    pointsRef.current = events.flatMap((e) => {
      const p = getEventPosition(e);
      if (!p) return [];
      const sev = e.severity as SeverityLevel;
      return [
        {
          lat: (p.lat * Math.PI) / 180,
          lng: (p.lng * Math.PI) / 180,
          color: SEVERITY_COLORS[sev] ?? "#ff6b3d",
          size: SEVERITY_SIZE[sev] ?? 2.4,
        },
      ];
    });
  }, [events]);

  const close = useCallback(() => {
    writeSeen();
    setLeaving(true);
    window.setTimeout(() => setOpen(false), 650);
  }, []);

  useEffect(() => {
    if (!open || leaving) return;
    const timer = window.setTimeout(close, AUTO_CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [open, leaving, close]);

  useEffect(() => {
    if (!open) return;
    buttonRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      // aria-modal: Tab must not reach the map behind the intro
      if (e.key === "Tab") {
        e.preventDefault();
        buttonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  useEffect(() => {
    if (!open) return;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const mask = landMask();
    const dots = lattice(DOTS).map(([lat, lng], i) => ({
      lat,
      lng,
      land: ((mask[i >> 3] ?? 0) >> (i & 7)) & 1,
    }));
    let raf = 0;
    let rot = 0.6;
    let last = performance.now();

    const draw = (now: number) => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const r = Math.min(w * 0.4, h * 0.27);
      const cx = w / 2;
      const cy = h * 0.36;

      if (!reduce) rot += ((now - last) / 1000) * 0.18;
      last = now;
      const cosT = Math.cos(TILT);
      const sinT = Math.sin(TILT);

      // Project lat/lng to screen with axial tilt; z > 0 faces the viewer
      const project = (lat: number, lng: number) => {
        const x0 = Math.cos(lat) * Math.sin(lng + rot);
        const y0 = Math.sin(lat);
        const z0 = Math.cos(lat) * Math.cos(lng + rot);
        const y = y0 * cosT - z0 * sinT;
        const z = y0 * sinT + z0 * cosT;
        return { x: cx + x0 * r, y: cy - y * r, z };
      };

      // Atmosphere: a thin halo outside the limb only
      const glow = ctx.createRadialGradient(cx, cy, r, cx, cy, r * 1.22);
      glow.addColorStop(0, "rgba(52,208,172,0.22)");
      glow.addColorStop(1, "rgba(52,208,172,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 1.22, 0, Math.PI * 2);
      ctx.fill();

      const rx = r * 1.3;
      const ry = r * 0.3;
      const cosO = Math.cos(ORBIT_TILT);
      const sinO = Math.sin(ORBIT_TILT);
      const orbitPoint = (a: number) => ({
        x: cx + Math.cos(a) * rx * cosO - Math.sin(a) * ry * sinO,
        y: cy + Math.cos(a) * rx * sinO + Math.sin(a) * ry * cosO,
      });
      const orbitArc = (from: number, to: number) => {
        ctx.strokeStyle = "rgba(52,208,172,0.4)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, ORBIT_TILT, from, to);
        ctx.stroke();
      };
      // The satellite runs the orbit; the upper half of the ellipse is behind
      const sa = reduce ? 0.6 : ((now / 1000) * 0.5) % (Math.PI * 2);
      const satBehind = sa > Math.PI;
      const drawSatellite = () => {
        const s = orbitPoint(sa);
        ctx.fillStyle = "#5edfc0";
        ctx.beginPath();
        ctx.arc(s.x, s.y, 2.6, 0, Math.PI * 2);
        ctx.fill();
      };

      orbitArc(Math.PI, Math.PI * 2);
      if (satBehind) drawSatellite();

      // Body, lit from the upper left
      const body = ctx.createRadialGradient(
        cx - r * 0.35,
        cy - r * 0.4,
        r * 0.1,
        cx,
        cy,
        r,
      );
      body.addColorStop(0, "#1a2b44");
      body.addColorStop(1, "#0a111d");
      ctx.fillStyle = body;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "rgba(52,208,172,0.35)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Lattice: land bright, sea faint, both fading toward the limb
      for (const d of dots) {
        const p = project(d.lat, d.lng);
        if (p.z < 0) continue;
        if (d.land) {
          ctx.fillStyle = `rgba(201,211,226,${0.25 + p.z * 0.7})`;
          ctx.fillRect(p.x - 1.1, p.y - 1.1, 2.2, 2.2);
        } else {
          ctx.fillStyle = `rgba(120,137,166,${0.06 + p.z * 0.16})`;
          ctx.fillRect(p.x - 0.6, p.y - 0.6, 1.2, 1.2);
        }
      }

      // Events: a core plus an expanding ring, phase-shifted per event
      const pts = pointsRef.current;
      pts.forEach((e, i) => {
        const p = project(e.lat, e.lng);
        if (p.z < 0.02) return;
        const phase = reduce ? 0.5 : (now / 1800 + i * 0.137) % 1;
        ctx.globalAlpha = (1 - phase) * 0.9 * p.z;
        ctx.strokeStyle = e.color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(p.x, p.y, e.size + phase * 16, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 0.5 + p.z * 0.5;
        ctx.fillStyle = e.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, e.size, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      orbitArc(0, Math.PI);
      if (!satBehind) drawSatellite();

      if (!reduce) raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [open]);

  if (!open) return null;
  const active = events.filter((e) => e.isActive).length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="intro-title"
      className={`fixed inset-0 z-[100] flex flex-col items-center justify-end overflow-hidden bg-gray-950 pb-[10vh] transition-[opacity,transform] duration-700 ease-[cubic-bezier(.6,0,.3,1)] ${
        leaving ? "pointer-events-none scale-[1.6] opacity-0" : "opacity-100"
      }`}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full"
        aria-hidden="true"
      />
      <div className="relative flex max-w-xl flex-col items-center px-6 text-center">
        <div className="mb-4 flex items-center gap-3 text-gray-100">
          <PhoenixMark className="h-10 w-10" />
          <h1
            id="intro-title"
            className="text-4xl font-semibold tracking-tight md:text-5xl"
          >
            Phoenix
          </h1>
        </div>
        <p className="text-balance text-base text-gray-300 md:text-lg">
          {t.intro.tagline}
        </p>
        <p className="mt-3 text-sm text-gray-400" aria-live="polite">
          {events.length > 0
            ? t.intro.activeNow.replace("{n}", String(active))
            : t.common.loading}
        </p>
        <div className="mt-8 flex items-center gap-3">
          <button
            ref={buttonRef}
            type="button"
            onClick={close}
            className="rounded-full bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-primary-700"
          >
            {t.intro.enter}
          </button>
        </div>
      </div>
    </div>
  );
}
