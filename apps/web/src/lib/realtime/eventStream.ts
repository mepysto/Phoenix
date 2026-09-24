/**
 * Live event notifications over the API's /ws/events WebSocket.
 *
 * The server sends notifications (event_created / event_updated /
 * event_merged) carrying an event id, not the full event. A sync can emit
 * hundreds at once, so ids are collected for `batchMs` and handed over in one
 * batch. After a reconnect the client may have missed messages, so
 * `onResync` asks the caller to refresh everything.
 */

export type StreamStatus = "connecting" | "live" | "reconnecting" | "stopped";

const CHANGE_TYPES = new Set(["event_created", "event_updated", "event_merged"]);

export interface EventStreamOptions {
  url: string;
  onChanges: (eventIds: string[]) => void;
  onResync: () => void;
  onStatus?: (status: StreamStatus) => void;
  batchMs?: number;
  pingMs?: number;
  maxBackoffMs?: number;
  /** Injectable for tests */
  createSocket?: (url: string) => WebSocket;
}

export class EventStream {
  private socket: WebSocket | null = null;
  private pending = new Set<string>();
  private flushTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private attempts = 0;
  private hasConnectedBefore = false;
  private stopped = true;

  constructor(private readonly options: EventStreamOptions) {}

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    this.clearTimers();
    this.pending.clear();
    const socket = this.socket;
    this.socket = null;
    socket?.close();
    this.options.onStatus?.("stopped");
  }

  private connect(): void {
    this.options.onStatus?.(this.hasConnectedBefore ? "reconnecting" : "connecting");
    const create = this.options.createSocket ?? ((url: string) => new WebSocket(url));
    const socket = create(this.options.url);
    this.socket = socket;

    socket.onopen = () => {
      if (socket !== this.socket) return;
      this.attempts = 0;
      this.options.onStatus?.("live");
      this.pingTimer = setInterval(() => socket.send("ping"), this.options.pingMs ?? 25_000);
      // Anything that happened while disconnected was never delivered
      if (this.hasConnectedBefore) this.options.onResync();
      this.hasConnectedBefore = true;
    };

    socket.onmessage = (message: MessageEvent) => {
      if (typeof message.data !== "string" || message.data === "pong") return;
      let payload: { type?: string; data?: { event_id?: string } };
      try {
        payload = JSON.parse(message.data);
      } catch {
        return; // not a notification
      }
      const id = payload.data?.event_id;
      if (payload.type && CHANGE_TYPES.has(payload.type) && id) {
        this.pending.add(id);
        this.scheduleFlush();
      }
    };

    socket.onclose = () => {
      if (socket !== this.socket) return;
      this.socket = null;
      if (this.pingTimer) clearInterval(this.pingTimer);
      this.pingTimer = null;
      if (!this.stopped) this.scheduleReconnect();
    };
  }

  private scheduleFlush(): void {
    if (this.flushTimer) return;
    this.flushTimer = setTimeout(() => {
      this.flushTimer = null;
      const ids = [...this.pending];
      this.pending.clear();
      if (ids.length) this.options.onChanges(ids);
    }, this.options.batchMs ?? 1_500);
  }

  private scheduleReconnect(): void {
    this.options.onStatus?.("reconnecting");
    // Exponential backoff with jitter so clients don't reconnect in lockstep
    const base = Math.min(1_000 * 2 ** this.attempts, this.options.maxBackoffMs ?? 30_000);
    this.attempts += 1;
    this.retryTimer = setTimeout(() => this.connect(), base / 2 + Math.random() * (base / 2));
  }

  private clearTimers(): void {
    for (const timer of [this.flushTimer, this.retryTimer]) if (timer) clearTimeout(timer);
    if (this.pingTimer) clearInterval(this.pingTimer);
    this.flushTimer = this.retryTimer = this.pingTimer = null;
  }
}

/** ws(s)://host/ws/events derived from the REST base URL. */
export function eventStreamUrl(apiUrl: string): string {
  return `${apiUrl.replace(/^http/, "ws").replace(/\/$/, "")}/ws/events`;
}
