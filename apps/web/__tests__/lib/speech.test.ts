import { afterEach, describe, expect, it, vi } from "vitest";
import { canListen, listenOnce, speak, speechLocale } from "@/lib/agent/speech";

class FakeRecognition {
  static last: FakeRecognition | null = null;
  lang = "";
  interimResults = true;
  maxAlternatives = 5;
  onresult: ((e: { results: { transcript: string }[][] }) => void) | null = null;
  onerror: ((e: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn(() => {
    FakeRecognition.last = this;
  });
  stop = vi.fn(() => this.onend?.());
}

afterEach(() => {
  delete (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
  vi.unstubAllGlobals();
});

describe("speech", () => {
  it("maps UI languages to speech locales", () => {
    expect(speechLocale("ko")).toBe("ko-KR");
    expect(speechLocale("xx")).toBe("en-US");
  });

  it("listens once and resolves with the transcript", async () => {
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition;
    expect(canListen()).toBe(true);
    const { result } = listenOnce("ko");
    const recognition = FakeRecognition.last!;
    expect(recognition.lang).toBe("ko-KR");
    recognition.onresult?.({ results: [[{ transcript: "도쿄 지진 보여줘" }]] });
    recognition.onend?.();
    await expect(result).resolves.toBe("도쿄 지진 보여줘");
  });

  it("treats silence as empty and real failures as errors", async () => {
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition;
    const silent = listenOnce("en");
    FakeRecognition.last!.onerror?.({ error: "no-speech" });
    await expect(silent.result).resolves.toBe("");
    const denied = listenOnce("en");
    FakeRecognition.last!.onerror?.({ error: "not-allowed" });
    await expect(denied.result).rejects.toThrow("not-allowed");
  });

  it("speaks in the UI language", () => {
    const spoken: { text: string; lang: string }[] = [];
    vi.stubGlobal("SpeechSynthesisUtterance", class {
      lang = "";
      constructor(public text: string) {}
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: { cancel: vi.fn(), speak: (u: { text: string; lang: string }) => spoken.push({ text: u.text, lang: u.lang }) },
    });
    speak("Hello", "fr");
    speak("   ", "fr");
    expect(spoken).toEqual([{ text: "Hello", lang: "fr-FR" }]);
  });
});
