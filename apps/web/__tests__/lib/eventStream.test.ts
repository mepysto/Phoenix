import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EventStream, eventStreamUrl, type StreamStatus } from "@/lib/realtime/eventStream";

class FakeSocket {
  static instances: FakeSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((m: { data: unknown }) => void) | null = null;
  onclose: (() => void) | null = null;
  sent: string[] = [];
  closed = false;
  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.closed = true;
  }
  // test helpers
  open() {
    this.onopen?.();
  }
  message(data: unknown) {
    this.onmessage?.({ data: typeof data === "string" ? data : JSON.stringify(data) });
  }
  drop() {
    this.onclose?.();
  }
}

const notification = (type: string, id: string) => ({ type, data: { event_id: id } });

function setup() {
  const onChanges = vi.fn();
  const onResync = vi.fn();
  const statuses: StreamStatus[] = [];
  const stream = new EventStream({
    url: "ws://api/ws/events",
    onChanges,
    onResync,
    onStatus: (s) => statuses.push(s),
    batchMs: 1000,
    createSocket: (url) => new FakeSocket(url) as unknown as WebSocket,
  });
  return { stream, onChanges, onResync, statuses };
}

describe("EventStream", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeSocket.instances = [];
  });
  afterEach(() => vi.useRealTimers());

  it("batches and de-duplicates notification ids", () => {
    const { stream, onChanges } = setup();
    stream.start();
    const socket = FakeSocket.instances[0]!;
    socket.open();
    socket.message(notification("event_created", "a"));
    socket.message(notification("event_updated", "b"));
    socket.message(notification("event_updated", "a"));
    expect(onChanges).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);
    expect(onChanges).toHaveBeenCalledOnce();
    expect(onChanges.mock.calls[0]![0].sort()).toEqual(["a", "b"]);
  });

  it("ignores pong, malformed and unrelated messages", () => {
    const { stream, onChanges } = setup();
    stream.start();
    const socket = FakeSocket.instances[0]!;
    socket.open();
    socket.message("pong");
    socket.message("{not json");
    socket.message({ type: "system_notice", data: { event_id: "x" } });
    vi.advanceTimersByTime(5000);
    expect(onChanges).not.toHaveBeenCalled();
  });

  it("reconnects with backoff and resyncs after a drop, not on first connect", () => {
    const { stream, onResync, statuses } = setup();
    stream.start();
    FakeSocket.instances[0]!.open();
    expect(onResync).not.toHaveBeenCalled();
    expect(statuses).toEqual(["connecting", "live"]);

    FakeSocket.instances[0]!.drop();
    expect(statuses.at(-1)).toBe("reconnecting");
    vi.advanceTimersByTime(1000); // first backoff is at most 1s
    expect(FakeSocket.instances).toHaveLength(2);

    FakeSocket.instances[1]!.open();
    expect(onResync).toHaveBeenCalledOnce(); // missed messages while offline
    expect(statuses.at(-1)).toBe("live");
  });

  it("sends keep-alive pings while live", () => {
    const { stream } = setup();
    stream.start();
    FakeSocket.instances[0]!.open();
    vi.advanceTimersByTime(25_000);
    expect(FakeSocket.instances[0]!.sent).toEqual(["ping"]);
  });

  it("stop() closes the socket and never reconnects or flushes", () => {
    const { stream, onChanges } = setup();
    stream.start();
    const socket = FakeSocket.instances[0]!;
    socket.open();
    socket.message(notification("event_created", "a"));
    stream.stop();
    socket.drop();
    vi.advanceTimersByTime(60_000);
    expect(socket.closed).toBe(true);
    expect(FakeSocket.instances).toHaveLength(1);
    expect(onChanges).not.toHaveBeenCalled();
  });

  it("derives ws/wss URLs from the API base URL", () => {
    expect(eventStreamUrl("http://localhost:28000")).toBe("ws://localhost:28000/ws/events");
    expect(eventStreamUrl("https://api.phoenix.org/")).toBe("wss://api.phoenix.org/ws/events");
  });
});
