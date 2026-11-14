import { eventTypeIcon } from "@/lib/eventTypeIcons";

/** The icon for an event type, the same one drawn on its map marker */
export function EventTypeIcon({ type, className = "h-4 w-4" }: { type: string; className?: string }) {
  const Icon = eventTypeIcon(type);
  return <Icon className={className} aria-hidden="true" />;
}
