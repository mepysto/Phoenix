"use client";

import { useEffect } from "react";

/** Register the service worker once (offline /lite, closed-tab alerts). */
export function ServiceWorker() {
  useEffect(() => {
    if (
      !("serviceWorker" in navigator) ||
      process.env.NODE_ENV !== "production"
    )
      return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Unsupported or blocked: the site works the same without it
    });
  }, []);
  return null;
}
