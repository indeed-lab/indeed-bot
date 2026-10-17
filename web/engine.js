/**
 * A self-contained, local browser frontend for Indeed-as-a-Service.
 *
 * Replies are imported from the generated native Lean export. Detection and
 * random sampling are JavaScript behavior outside the source-level Lean proof.
 * No prompts are stored, transmitted, or sent to a language model.
 */
import { francAll } from "franc-min";
import { replyCatalog } from "./replies.generated.js";

export const supportedLanguages = Object.freeze({
  en: "English",
  zh: "中文",
  ja: "日本語",
  ko: "한국어",
  es: "Español",
  fr: "Français",
  de: "Deutsch",
  pt: "Português",
  ru: "Русский",
  ar: "العربية",
});

export const maxInputLength = 8000;

const latinCodes = Object.freeze({ eng: "en", fra: "fr", deu: "de", spa: "es", por: "pt" });
const latinHints = Object.freeze({
  en: new Set("the this that with your you thanks hello yes does should would could think really because very have has are is and for but not been our".split(" ")),
  fr: new Set("bonjour salut merci beaucoup cette cet est sont avec vous nous pas une des les pour très mais aussi votre peut être bien français française".split(" ")),
  de: new Set("der die das ist sind und ich nicht ein eine für mit haben wir sehr aber auch dieser dieses danke guten bitte mein kann können schön wirklich".split(" ")),
  es: new Set("hola gracias esto esta es son con usted ustedes nosotros muy pero también puede tiene tengo qué bueno buenos días sí sabes español española".split(" ")),
  pt: new Set("olá obrigado obrigada isto isso é são com você vocês nós muito mas também pode tem tenho bom boa não sim seu português portuguesa".split(" ")),
});

// Franc's trigram model is designed for running text. These recognizable short
// greetings avoid asking it to infer a language from just a handful of letters.
// This is detector vocabulary, not a second copy of the agreement catalog.
const shortGreetings = Object.freeze({
  en: new Set(["hello", "hi", "hey", "thanks", "thank you", "good morning", "good evening"]),
  fr: new Set(["bonjour", "salut", "merci", "merci beaucoup", "bonsoir"]),
  de: new Set(["hallo", "danke", "guten tag", "guten morgen", "guten abend", "danke schön"]),
  es: new Set(["hola", "gracias", "buenos días", "buenas tardes", "buenas noches"]),
  pt: new Set(["olá", "obrigado", "obrigada", "bom dia", "boa tarde", "boa noite"]),
});

for (const locale of Object.keys(supportedLanguages)) {
  const pool = replyCatalog[locale];
  if (!Array.isArray(pool) || !pool.length || pool.some((text) => typeof text !== "string" || !text.trim())) {
    throw new Error(`The generated reply catalog has an invalid ${locale} pool.`);
  }
}
if (Object.keys(replyCatalog).length !== Object.keys(supportedLanguages).length) {
  throw new Error("The generated reply catalog does not match the supported languages.");
}

function decision(language, source, reason, requested = "auto") {
  return { language, detection: { requested, source, reason } };
}

function fallback(reason) {
  return decision("en", "fallback", `${reason}; using English.`);
}

function validateInput(text) {
  if (typeof text !== "string") throw new TypeError("Input must be a string.");
  if (!text.trim()) throw new RangeError("Input must contain non-whitespace text.");
  if (text.length > maxInputLength) {
    throw new RangeError(`Input must be at most ${maxInputLength} characters.`);
  }
}

/**
 * Best-effort routing within ten supported languages.
 *
 * The browser uses script heuristics, common-word evidence, and Franc's Latin
 * trigram model; it does not run the Python CLI's Lingua detector. Shared scripts,
 * mixed text, short messages, and unsupported languages remain ambiguous. Franc
 * scores are normalized distances, not calibrated probabilities.
 */
export function detectLanguage(text, requested = "auto") {
  validateInput(text);
  if (requested !== "auto") {
    if (!Object.hasOwn(supportedLanguages, requested)) {
      throw new RangeError(`Unsupported language: ${String(requested)}.`);
    }
    return decision(requested, "override", "Language explicitly selected by the caller.", requested);
  }

  const normalized = text.normalize("NFKC");
  const letters = normalized.match(/\p{L}/gu) ?? [];
  if (!letters.length) return fallback("No alphabetic text");

  // Script properties also include some digits and punctuation. Compare only
  // letters so Arabic-Indic numbers cannot outweigh a Latin-language sentence.
  const count = (pattern) => (normalized.match(pattern) ?? []).filter((letter) => /\p{L}/u.test(letter)).length;
  const kana = count(/[\p{Script=Hiragana}\p{Script=Katakana}]/gu);
  const han = count(/\p{Script=Han}/gu);
  const hangul = count(/\p{Script=Hangul}/gu);
  const scripts = [
    ["ja", kana ? kana + han : 0],
    ["zh", kana ? 0 : han],
    ["ko", hangul],
    ["ru", count(/\p{Script=Cyrillic}/gu)],
    ["ar", count(/\p{Script=Arabic}/gu)],
    ["latin", count(/\p{Script=Latin}/gu)],
  ].sort((a, b) => b[1] - a[1]);

  const [script, amount] = scripts[0];
  if (amount / letters.length < 0.6) return fallback("Mixed or unsupported script evidence");
  if (script !== "latin") {
    return decision(script, "script", "Dominant script routed within the supported language set.");
  }

  const tokens = normalized.toLocaleLowerCase("en").match(/[\p{L}\p{M}]+/gu) ?? [];
  const phrase = tokens.join(" ");
  for (const [locale, phrases] of Object.entries(shortGreetings)) {
    if (phrases.has(phrase)) return decision(locale, "lexicon", "Recognized a common short greeting.");
  }

  const words = new Set(tokens);
  const evidence = Object.entries(latinHints)
    .map(([locale, hints]) => [locale, [...words].filter((word) => hints.has(word)).length])
    .sort((a, b) => b[1] - a[1]);
  const [bestHint, hits] = evidence[0];
  const runnerHits = evidence[1][1];
  if (hits >= 2 && hits - runnerHits >= 2) {
    return decision(bestHint, "lexicon", "Distinctive common-word evidence within the supported language set.");
  }
  if (hits > 0 && hits === runnerHits && letters.length < 80) {
    return fallback("Conflicting common-word evidence");
  }
  if (letters.length < 8) return fallback("Too little language evidence");

  const scores = francAll(normalized, { only: Object.keys(latinCodes), minLength: 8 });
  const [best, score] = scores[0] ?? ["und", 0];
  const nextScore = scores[1]?.[1] ?? 0;
  const minimumGap = letters.length < 20 ? 0.2 : 0.08;
  if (!Object.hasOwn(latinCodes, best) || score <= 0 || score - nextScore < minimumGap) {
    return fallback("Ambiguous language evidence");
  }
  return decision(latinCodes[best], "franc", "Best supported Latin-language match passed the routing heuristic.");
}

/**
 * Uniform integer in [0, size), using rejection sampling over Web Crypto.
 * The optional provider makes boundary behavior testable without changing reply.
 */
export function uniformIndex(size, cryptoProvider = globalThis.crypto) {
  const range = 2 ** 32;
  if (!Number.isSafeInteger(size) || size < 1 || size > range) {
    throw new RangeError("Pool size must be an integer between 1 and 2^32.");
  }
  if (!cryptoProvider || typeof cryptoProvider.getRandomValues !== "function") {
    throw new Error("Secure randomness is unavailable in this browser.");
  }
  const limit = Math.floor(range / size) * size;
  const buffer = new Uint32Array(1);
  do {
    cryptoProvider.getRandomValues(buffer);
  } while (buffer[0] >= limit);
  return buffer[0] % size;
}

/**
 * Select one localized agreement, without retaining the input.
 * @param {string} text
 * @param {{language?: string}} [options]
 * @returns {{text: string, language: string, index: number, detection: object}}
 */
export function reply(text, options = {}) {
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new TypeError("Options must be an object.");
  }
  const { language, detection } = detectLanguage(text, options.language ?? "auto");
  const pool = replyCatalog[language];
  const index = uniformIndex(pool.length);
  return { text: pool[index], language, index, detection };
}
