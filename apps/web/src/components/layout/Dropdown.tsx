"use client";

import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

/**
 * A disclosure menu: a trigger button and a panel that closes on outside
 * click, Escape (returning focus to the trigger) and navigation.
 */
export function Dropdown({
  trigger,
  triggerLabel,
  triggerClassName,
  panelClassName = "",
  align = "end",
  children,
}: {
  trigger: React.ReactNode;
  /** Accessible name when the trigger shows only an icon */
  triggerLabel?: string;
  triggerClassName: string | ((open: boolean) => string);
  panelClassName?: string;
  align?: "start" | "end";
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={root} className="relative">
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={triggerLabel}
        onClick={() => setOpen((o) => !o)}
        className={typeof triggerClassName === "function" ? triggerClassName(open) : triggerClassName}
      >
        {trigger}
      </button>
      {open && (
        <div
          id={panelId}
          // Links inside close the menu on navigation; buttons inside can call blur
          onClick={(e) => {
            if ((e.target as HTMLElement).closest("a")) setOpen(false);
          }}
          className={`absolute top-full z-[70] mt-2 animate-panel-in rounded-xl border border-gray-700 bg-gray-900 p-1.5 shadow-panel ${
            align === "end" ? "end-0" : "start-0"
          } ${panelClassName}`}
        >
          {children}
        </div>
      )}
    </div>
  );
}
