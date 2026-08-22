export type VoiceOptions = {
  rate?: number;
  pitch?: number;
  volume?: number;
  lang?: string;
};

class VoiceAgent {
  private currentUtterance: SpeechSynthesisUtterance | null = null;

  /**
   * Speak any dynamic text.
   *
   * This is intentionally independent of the question/page.
   * Whatever text the AI or UI provides can be spoken.
   */
  speak(text: string, options: VoiceOptions = {}) {
    if (typeof window === "undefined") return;
    if (!text?.trim()) return;

    this.stop();

    const cleanText = this.cleanText(text);

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);

    utterance.rate = options.rate ?? 0.85;
    utterance.pitch = options.pitch ?? 1;
    utterance.volume = options.volume ?? 1;
    utterance.lang = options.lang ?? "en-US";

    this.setPreferredVoice(utterance, options.lang ?? "en-US");

    this.currentUtterance = utterance;

    utterance.onend = () => {
      if (this.currentUtterance === utterance) {
        this.currentUtterance = null;
      }
    };

    utterance.onerror = () => {
      if (this.currentUtterance === utterance) {
        this.currentUtterance = null;
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  /**
   * Speak a piece of text while allowing the caller
   * to provide dynamic language/settings.
   */
  speakDynamic(
    text: string,
    options: VoiceOptions = {},
  ) {
    this.speak(text, options);
  }

  stop() {
    if (typeof window === "undefined") return;

    window.speechSynthesis.cancel();
    this.currentUtterance = null;
  }

  pause() {
    if (typeof window === "undefined") return;

    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
    }
  }

  resume() {
    if (typeof window === "undefined") return;

    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  }

  isSpeaking() {
    if (typeof window === "undefined") return false;

    return window.speechSynthesis.speaking;
  }

  /**
   * Returns the available browser voices.
   */
  getVoices(): SpeechSynthesisVoice[] {
    if (typeof window === "undefined") return [];

    return window.speechSynthesis.getVoices();
  }

  private setPreferredVoice(
    utterance: SpeechSynthesisUtterance,
    language: string,
  ) {
    const voices = this.getVoices();

    if (!voices.length) return;

    const preferredVoice =
      voices.find((voice) =>
        voice.name.toLowerCase().includes("google us english"),
      ) ||
      voices.find((voice) =>
        voice.name.toLowerCase().includes("microsoft zira"),
      ) ||
      voices.find((voice) =>
        voice.lang.toLowerCase() === language.toLowerCase(),
      ) ||
      voices.find((voice) =>
        voice.lang.toLowerCase().startsWith(
          language.split("-")[0].toLowerCase(),
        ),
      ) ||
      voices.find((voice) =>
        voice.lang.toLowerCase().startsWith("en"),
      );

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }
  }

  /**
   * Converts UI/AI-generated content into natural speech.
   *
   * It does NOT care what page generated the text.
   */
  private cleanText(text: string) {
    return text
      // Markdown headings
      .replace(/^#{1,6}\s*/gm, "")

      // Markdown bold / italic
      .replace(/\*\*(.*?)\*\*/g, "$1")
      .replace(/__(.*?)__/g, "$1")
      .replace(/\*(.*?)\*/g, "$1")
      .replace(/_(.*?)_/g, "$1")

      // Code formatting
      .replace(/```[\s\S]*?```/g, "")
      .replace(/`([^`]+)`/g, "$1")

      // Markdown links: keep the visible text
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")

      // Remove common bullet characters
      .replace(/^\s*[-•]\s*/gm, "")

      // Remove repeated hashes
      .replace(/###/g, "")
      .replace(/##/g, "")
      .replace(/#/g, "")

      // Convert line breaks into natural pauses
      .replace(/\n+/g, ". ")

      // Remove extra spaces
      .replace(/\s+/g, " ")

      .trim();
  }
}

export const voiceAgent = new VoiceAgent();