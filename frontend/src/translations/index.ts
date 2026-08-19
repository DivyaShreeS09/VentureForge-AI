import { en } from "./en";
import { ta } from "./ta";
import { te } from "./te";
import { hi } from "./hi";

export const translations = {
  en,
  ta,
  te,
  hi,
};

export type TranslationLanguage = keyof typeof translations;