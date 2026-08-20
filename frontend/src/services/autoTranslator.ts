const cache = new Map<string, string>();

const languageNames: Record<string, string> = {
  en: "English",
  hi: "Hindi",
  ta: "Tamil",
  te: "Telugu",
};

export async function translateText(
  text: string,
  language: string,
): Promise<string> {
  if (!text.trim() || language === "en") {
    return text;
  }

  const cacheKey = `${language}:${text}`;

  const cached = cache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const languageName = languageNames[language];

  if (!languageName) {
    return text;
  }

  try {
    const response = await fetch(
      "http://127.0.0.1:8000/api/translate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          target_language: language,
        }),
      },
    );

    if (!response.ok) {
      console.error("Translation request failed:", response.status);
      return text;
    }

    const data = await response.json();

    const translated = data.translated_text;

    if (typeof translated !== "string" || !translated.trim()) {
      return text;
    }

    cache.set(cacheKey, translated);

    return translated;
  } catch (error) {
    console.error("Translation error:", error);
    return text;
  }
}

export function clearTranslationCache() {
  cache.clear();
}
