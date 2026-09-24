/**
 * Voice for the map assistant via the browser's Web Speech API (M7): speech
 * recognition for questions, speech synthesis for answers. No extra service
 * or key; availability depends on the browser (Chrome/Edge/Safari).
 */

const LOCALES: Record<string, string> = {
  en: "en-US",
  ko: "ko-KR",
  zh: "zh-CN",
  es: "es-ES",
  fr: "fr-FR",
  ru: "ru-RU",
  ar: "ar-SA",
};

export const speechLocale = (lang: string) => LOCALES[lang] ?? "en-US";

interface RecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface Recognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type RecognitionConstructor = new () => Recognition;

function recognitionClass(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export const canListen = () => recognitionClass() !== null;
export const canSpeak = () => typeof window !== "undefined" && "speechSynthesis" in window;

/** Listen for one utterance; resolves with the transcript ("" if nothing was heard) */
export function listenOnce(lang: string): { result: Promise<string>; stop: () => void } {
  const Class = recognitionClass();
  if (!Class) return { result: Promise.reject(new Error("speech recognition unavailable")), stop: () => {} };
  const recognition = new Class();
  recognition.lang = speechLocale(lang);
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  const result = new Promise<string>((resolve, reject) => {
    let heard = "";
    recognition.onresult = (event) => {
      heard = Array.from(event.results)
        .map((alternatives) => alternatives[0]?.transcript ?? "")
        .join(" ")
        .trim();
    };
    recognition.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "aborted") resolve("");
      else reject(new Error(event.error));
    };
    recognition.onend = () => resolve(heard);
  });
  recognition.start();
  return { result, stop: () => recognition.stop() };
}

/** Read text aloud in the UI language (cancels anything still speaking) */
export function speak(text: string, lang: string): void {
  if (!canSpeak() || !text.trim()) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = speechLocale(lang);
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (canSpeak()) window.speechSynthesis.cancel();
}
