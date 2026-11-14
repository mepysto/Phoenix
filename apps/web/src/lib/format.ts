/**
 * One date style across the app. Absolute dates use the reader's language
 * ("20 Oct 2026"), never a bare numeric form whose order varies by country;
 * recent moments read as relative time ("3 hours ago").
 */

type DateInput = string | number | Date;

const toDate = (v: DateInput) => (v instanceof Date ? v : new Date(v));

export function formatDate(value: DateInput, lang: string): string {
  return toDate(value).toLocaleDateString(lang, { dateStyle: "medium" });
}

export function formatDateTime(value: DateInput, lang: string): string {
  return toDate(value).toLocaleString(lang, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

/** "3 hours ago" / "in 2 days"; under a minute reads as "now" */
export function formatRelative(
  value: DateInput,
  lang: string,
  now: number = Date.now(),
): string {
  const seconds = Math.round((toDate(value).getTime() - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) {
      return rtf.format(Math.trunc(seconds / size), unit);
    }
  }
  return rtf.format(0, "second");
}

/** Relative within a week, the date after that: what a list row should show */
export function formatWhen(
  value: DateInput,
  lang: string,
  now: number = Date.now(),
): string {
  const age = Math.abs(now - toDate(value).getTime());
  return age < 7 * 24 * 3600 * 1000
    ? formatRelative(value, lang, now)
    : formatDate(value, lang);
}

/**
 * A moment on a detail view: how long ago, then the exact time in UTC so
 * readers in different time zones agree ("3 hours ago · Nov 2, 2026, 09:18 UTC").
 */
export function formatMoment(
  value: DateInput,
  lang: string,
  now: number = Date.now(),
): string {
  const exact = toDate(value).toLocaleString(lang, {
    dateStyle: "medium",
    timeStyle: "short",
    hourCycle: "h23",
    timeZone: "UTC",
  });
  return `${formatRelative(value, lang, now)} · ${exact} UTC`;
}
