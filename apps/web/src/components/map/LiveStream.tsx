"use client";

import { useEffect, useRef } from "react";

/**
 * Plays a public camera's HLS stream in the browser: hls.js (loaded on
 * demand) wherever Media Source Extensions exist, native HLS otherwise
 * (iOS Safari). hls.js comes first on purpose: recent Chrome also reports
 * native HLS support, but its native player failed on Caltrans' responses
 * (ERR_CONTENT_DECODING_FAILED). Calls onError when the stream cannot play;
 * many listed streams are offline.
 */
export function LiveStream({ src, label, onError }: { src: string; label: string; onError: () => void }) {
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const element = video.current;
    if (!element) return;
    let destroyed = false;
    let cleanup = () => {};

    void import("hls.js").then(({ default: Hls }) => {
      if (destroyed) return;
      if (Hls.isSupported()) {
        const hls = new Hls({
          lowLatencyMode: true,
          maxBufferLength: 10,
          // Offline Caltrans cameras answer 404 only after ~9 s: give up after 6 s
          // without retrying (working streams answer at once; the user can retry)
          manifestLoadPolicy: {
            default: {
              maxTimeToFirstByteMs: 6000,
              maxLoadTimeMs: 8000,
              timeoutRetry: { maxNumRetry: 0, retryDelayMs: 0, maxRetryDelayMs: 0 },
              errorRetry: { maxNumRetry: 0, retryDelayMs: 0, maxRetryDelayMs: 0 },
            },
          },
        });
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (!data.fatal) return;
          console.warn("Live stream failed", data.type, data.details, data.response?.code ?? "");
          onError();
        });
        hls.loadSource(src);
        hls.attachMedia(element);
        cleanup = () => hls.destroy();
      } else if (element.canPlayType("application/vnd.apple.mpegurl")) {
        element.src = src;
        element.onerror = () => onError();
        cleanup = () => {
          element.removeAttribute("src");
          element.load();
        };
      } else {
        onError();
      }
    });
    return () => {
      destroyed = true;
      cleanup();
    };
  }, [src, onError]);

  return (
    <video
      ref={video}
      autoPlay
      muted
      playsInline
      controls
      aria-label={label}
      className="aspect-video w-full bg-black object-contain"
    />
  );
}
