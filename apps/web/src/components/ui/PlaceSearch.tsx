"use client";

import { useEffect, useId, useState } from "react";
import { MapPin, Search } from "lucide-react";
import { placesAPI, type ApiPlace } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";

const MIN_CHARS = 2;
const DEBOUNCE_MS = 200;

/** "Valencia, Carabobo, Venezuela" */
export function placeLabel(place: ApiPlace): string {
  return [place.name, place.admin1, place.country].filter(Boolean).join(", ");
}

/**
 * Find a town or city by name in any language (ARIA combobox). Results come
 * from the Phoenix server's GeoNames copy, so typing never leaves Phoenix.
 */
export function PlaceSearch({
  label,
  onPick,
}: {
  label?: string;
  onPick: (place: ApiPlace) => void;
}) {
  const { t } = useTranslation();
  const id = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ApiPlace[] | null>(null);
  const [active, setActive] = useState(-1);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const q = query.trim();
    if (q.length < MIN_CHARS) {
      setResults(null);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      placesAPI
        .search(q, controller.signal)
        .then((places) => {
          setResults(places);
          setActive(places.length ? 0 : -1);
          setOpen(true);
        })
        .catch(() => {
          if (!controller.signal.aborted) setResults([]);
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const pick = (place: ApiPlace) => {
    onPick(place);
    setQuery("");
    setResults(null);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!results?.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + results.length) % results.length);
    } else if (e.key === "Enter" && open && active >= 0) {
      e.preventDefault();
      pick(results[active]!);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const listId = `${id}-places`;
  const showList = open && results !== null;
  return (
    <div className="relative">
      <label htmlFor={`${id}-input`} className="field-label">
        {label ?? t.ux.placeSearchLabel}
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
        <input
          id={`${id}-input`}
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={showList && active >= 0 ? `${listId}-${active}` : undefined}
          autoComplete="off"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => results && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={t.ux.placeSearchPlaceholder}
          className="field !ps-9"
        />
      </div>
      {showList && (
        <div className="absolute inset-x-0 top-full z-20 mt-1 overflow-hidden rounded-lg border border-gray-700 bg-gray-900 shadow-panel">
          <ul id={listId} role="listbox" aria-label={label ?? t.ux.placeSearchLabel}>
            {results.length === 0 && <li className="px-3 py-2 text-sm text-gray-400">{t.ux.placeNoMatch}</li>}
            {results.map((place, i) => (
              <li
                key={place.id}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                // mousedown: pick before the input's blur closes the list
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(place);
                }}
                onMouseEnter={() => setActive(i)}
                className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-sm ${
                  i === active ? "bg-gray-800 text-white" : "text-gray-200"
                }`}
              >
                <MapPin className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
                <span className="truncate">{placeLabel(place)}</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-gray-800 px-3 py-1.5 text-xs text-gray-400">{t.ux.placeAttribution}</p>
        </div>
      )}
    </div>
  );
}
