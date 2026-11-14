import type { ApiDisasterEvent } from "@/lib/api/client";
import { formatPosition, getEventPosition } from "@/lib/eventPosition";

// USGS: "M 4.7 - 54 km NW of San Antonio de los Cobres, Argentina"
const USGS_TITLE = /^M\s?\d+(?:\.\d+)?\s*-\s*(.+)$/;
// GDACS and others: "Flood in Mozambique and South Africa"
const IN_PLACE = /\bin\s+(.+)$/;

/**
 * A place a reader recognises (UX plan L-03): country, region, then the
 * place named in the title, and coordinates only when nothing else is known.
 */
export function placeName(event: ApiDisasterEvent): string {
  const { country, region } = event.location;
  if (country) return country;
  if (region) return region;

  const usgs = USGS_TITLE.exec(event.title);
  if (usgs) {
    const rest = usgs[1]!.trim();
    const of = rest.lastIndexOf(" of ");
    return of >= 0 ? rest.slice(of + 4).trim() : rest;
  }
  const inPlace = IN_PLACE.exec(event.title);
  if (inPlace) return inPlace[1]!.trim();

  return formatPosition(getEventPosition(event));
}
