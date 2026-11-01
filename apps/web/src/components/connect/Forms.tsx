"use client";

import { useState } from "react";
import { MapPin } from "lucide-react";
import {
  CATEGORIES,
  communityAPI,
  type Category,
  type Need,
  type NeedPriority,
  type Offer,
  type OfferType,
  type OrgSummary,
} from "@/lib/api/community";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { CategoryIcon } from "./CategoryIcon";

export interface EventChoice {
  id: string;
  title: string;
  lat?: number | null;
  lng?: number | null;
}

const PRIORITIES: NeedPriority[] = ["critical", "high", "medium", "low"];
const OFFER_TYPES: OfferType[] = [
  "goods",
  "funding",
  "service",
  "volunteer",
  "transport",
  "other",
];

function CategoryPicker({
  value,
  onChange,
}: {
  value: Category[];
  onChange: (v: Category[]) => void;
}) {
  const { t } = useTranslation();
  return (
    <fieldset>
      <legend className="field-label">{t.connect.form.categories}</legend>
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((c) => {
          const on = value.includes(c);
          return (
            <button
              key={c}
              type="button"
              aria-pressed={on}
              onClick={() =>
                onChange(on ? value.filter((x) => x !== c) : [...value, c])
              }
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                on
                  ? "border-primary-400 bg-primary-400/15 text-primary-100"
                  : "border-gray-700 text-gray-300 hover:border-gray-500"
              }`}
            >
              <CategoryIcon category={c} className="h-3.5 w-3.5" />
              {t.connect.categories[c]}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

function numberOrNull(v: string): number | null {
  if (v.trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function SiteFields({
  place,
  lat,
  lng,
  set,
  event,
}: {
  place: string;
  lat: string;
  lng: string;
  set: (k: "place" | "lat" | "lng", v: string) => void;
  event?: EventChoice;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="f-place" className="field-label">
          {t.connect.form.place}
        </label>
        <input
          id="f-place"
          className="field"
          value={place}
          onChange={(e) => set("place", e.target.value)}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="f-lat" className="field-label">
            {t.connect.form.latitude}
          </label>
          <input
            id="f-lat"
            inputMode="decimal"
            className="field"
            value={lat}
            onChange={(e) => set("lat", e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="f-lng" className="field-label">
            {t.connect.form.longitude}
          </label>
          <input
            id="f-lng"
            inputMode="decimal"
            className="field"
            value={lng}
            onChange={(e) => set("lng", e.target.value)}
          />
        </div>
      </div>
      {event?.lat != null && event.lng != null && (
        <button
          type="button"
          onClick={() => {
            set("lat", event.lat!.toFixed(4));
            set("lng", event.lng!.toFixed(4));
          }}
          className="flex items-center gap-1.5 text-xs font-medium text-primary-300 hover:text-primary-200"
        >
          <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
          {event.title}
        </button>
      )}
      <p className="text-xs text-gray-400">{t.connect.form.sitesOnly}</p>
    </div>
  );
}

function EventSelect({
  events,
  value,
  onChange,
}: {
  events: EventChoice[];
  value: string;
  onChange: (v: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <div>
      <label htmlFor="f-event" className="field-label">
        {t.connect.form.event}
      </label>
      <select
        id="f-event"
        className="field"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{t.connect.form.noEvent}</option>
        {events.map((e) => (
          <option key={e.id} value={e.id}>
            {e.title}
          </option>
        ))}
      </select>
    </div>
  );
}

function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="rounded-lg border border-ember-600/50 bg-ember-700/10 px-3 py-2 text-sm text-ember-300"
    >
      {message}
    </p>
  );
}

export function NeedForm({
  orgs,
  events,
  initialEventId,
  onDone,
  onCancel,
}: {
  orgs: OrgSummary[];
  events: EventChoice[];
  initialEventId?: string;
  onDone: (need: Need) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const f = t.connect.form;
  const [orgId, setOrgId] = useState(orgs[0]?.id ?? "");
  const [eventId, setEventId] = useState(initialEventId ?? "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [priority, setPriority] = useState<NeedPriority>("high");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [beneficiaries, setBeneficiaries] = useState("");
  const [site, setSite] = useState({ place: "", lat: "", lng: "" });
  const [visibility, setVisibility] = useState<"public" | "org_only">("public");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const event = events.find((e) => e.id === eventId);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (categories.length === 0) return setError(f.pickCategory);
    setBusy(true);
    setError(null);
    try {
      const need = await communityAPI.createNeed({
        org_id: orgId,
        event_id: eventId || null,
        title,
        description: description || null,
        categories,
        priority,
        quantity: numberOrNull(quantity),
        unit: unit || null,
        beneficiaries: numberOrNull(beneficiaries),
        latitude: numberOrNull(site.lat),
        longitude: numberOrNull(site.lng),
        place_name: site.place || null,
        visibility,
      });
      onDone(need);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5">
      {orgs.length > 1 && (
        <div>
          <label htmlFor="f-org" className="field-label">
            {f.org}
          </label>
          <select
            id="f-org"
            className="field"
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <EventSelect events={events} value={eventId} onChange={setEventId} />
      <div>
        <label htmlFor="f-title" className="field-label">
          {f.titleField}
        </label>
        <input
          id="f-title"
          required
          minLength={3}
          maxLength={200}
          className="field"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <CategoryPicker value={categories} onChange={setCategories} />
      <fieldset>
        <legend className="field-label">{f.priority}</legend>
        <div className="grid grid-cols-4 gap-2">
          {PRIORITIES.map((p) => (
            <label
              key={p}
              className={`cursor-pointer rounded-lg border px-2 py-2 text-center text-xs font-medium ${
                priority === p
                  ? "border-ember-400 bg-ember-500/10 text-ember-300"
                  : "border-gray-700 text-gray-300"
              }`}
            >
              <input
                type="radio"
                name="priority"
                value={p}
                checked={priority === p}
                onChange={() => setPriority(p)}
                className="sr-only"
              />
              {t.connect.priority[p]}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label htmlFor="f-qty" className="field-label">
            {f.quantity}
          </label>
          <input
            id="f-qty"
            inputMode="numeric"
            className="field"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="f-unit" className="field-label">
            {f.unit}
          </label>
          <input
            id="f-unit"
            maxLength={40}
            className="field"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="f-ben" className="field-label">
            {f.beneficiaries}
          </label>
          <input
            id="f-ben"
            inputMode="numeric"
            className="field"
            value={beneficiaries}
            onChange={(e) => setBeneficiaries(e.target.value)}
          />
        </div>
      </div>
      <div>
        <label htmlFor="f-desc" className="field-label">
          {f.description}
        </label>
        <textarea
          id="f-desc"
          rows={4}
          maxLength={4000}
          className="field"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <SiteFields
        place={site.place}
        lat={site.lat}
        lng={site.lng}
        event={event}
        set={(k, v) => setSite((s) => ({ ...s, [k]: v }))}
      />
      <div>
        <label htmlFor="f-vis" className="field-label">
          {f.visibility}
        </label>
        <select
          id="f-vis"
          className="field"
          value={visibility}
          onChange={(e) =>
            setVisibility(e.target.value as "public" | "org_only")
          }
        >
          <option value="public">{f.public}</option>
          <option value="org_only">{f.orgOnly}</option>
        </select>
      </div>
      <FormError message={error} />
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-ghost" onClick={onCancel}>
          {f.cancel}
        </button>
        <button type="submit" className="btn-primary" disabled={busy || !orgId}>
          {f.submitNeed}
        </button>
      </div>
    </form>
  );
}

export function OfferForm({
  events,
  initialEventId,
  onDone,
  onCancel,
}: {
  events: EventChoice[];
  initialEventId?: string;
  onDone: (offer: Offer) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const f = t.connect.form;
  const [eventId, setEventId] = useState(initialEventId ?? "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [offerType, setOfferType] = useState<OfferType>("goods");
  const [categories, setCategories] = useState<Category[]>([]);
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("");
  const [site, setSite] = useState({ place: "", lat: "", lng: "" });
  const [visibility, setVisibility] = useState<"public" | "private">("public");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (categories.length === 0) return setError(f.pickCategory);
    setBusy(true);
    setError(null);
    try {
      const offer = await communityAPI.createOffer({
        event_id: eventId || null,
        title,
        description: description || null,
        offer_type: offerType,
        categories,
        quantity: numberOrNull(quantity),
        unit: unit || null,
        latitude: numberOrNull(site.lat),
        longitude: numberOrNull(site.lng),
        place_name: site.place || null,
        visibility,
      });
      onDone(offer);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5">
      <fieldset>
        <legend className="field-label">{f.offerType}</legend>
        <div className="grid grid-cols-3 gap-2">
          {OFFER_TYPES.map((o) => (
            <label
              key={o}
              className={`cursor-pointer rounded-lg border px-2 py-2 text-center text-xs font-medium ${
                offerType === o
                  ? "border-primary-400 bg-primary-400/15 text-primary-100"
                  : "border-gray-700 text-gray-300"
              }`}
            >
              <input
                type="radio"
                name="offerType"
                value={o}
                checked={offerType === o}
                onChange={() => setOfferType(o)}
                className="sr-only"
              />
              {t.connect.offerTypes[o]}
            </label>
          ))}
        </div>
      </fieldset>
      <EventSelect events={events} value={eventId} onChange={setEventId} />
      <div>
        <label htmlFor="o-title" className="field-label">
          {f.titleField}
        </label>
        <input
          id="o-title"
          required
          minLength={3}
          maxLength={200}
          className="field"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <CategoryPicker value={categories} onChange={setCategories} />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="o-qty" className="field-label">
            {f.quantity}
          </label>
          <input
            id="o-qty"
            inputMode="numeric"
            className="field"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="o-unit" className="field-label">
            {f.unit}
          </label>
          <input
            id="o-unit"
            maxLength={40}
            className="field"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
          />
        </div>
      </div>
      <div>
        <label htmlFor="o-desc" className="field-label">
          {f.description}
        </label>
        <textarea
          id="o-desc"
          rows={4}
          maxLength={4000}
          className="field"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <SiteFields
        place={site.place}
        lat={site.lat}
        lng={site.lng}
        set={(k, v) => setSite((s) => ({ ...s, [k]: v }))}
      />
      <div>
        <label htmlFor="o-vis" className="field-label">
          {f.visibility}
        </label>
        <select
          id="o-vis"
          className="field"
          value={visibility}
          onChange={(e) =>
            setVisibility(e.target.value as "public" | "private")
          }
        >
          <option value="public">{f.public}</option>
          <option value="private">{f.private}</option>
        </select>
      </div>
      <FormError message={error} />
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-ghost" onClick={onCancel}>
          {f.cancel}
        </button>
        <button type="submit" className="btn-primary" disabled={busy}>
          {f.submitOffer}
        </button>
      </div>
    </form>
  );
}
