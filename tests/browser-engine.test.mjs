import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { detectLanguage, maxInputLength, reply, supportedLanguages, uniformIndex } from "../web/engine.js";
import { replyCatalog } from "../web/replies.generated.js";

const examples = {
  en: "This algorithm is very fast and easy to understand.",
  zh: "这个算法的运行速度非常快，我觉得我们应该继续优化它。",
  ja: "このアルゴリズムはとても速いので、もっと詳しく調べたいです。",
  ko: "이 알고리즘은 정말 빠르고 사용하기도 편리합니다.",
  es: "Este algoritmo es muy rápido y fácil de entender.",
  fr: "Cet algorithme est très rapide et facile à comprendre.",
  de: "Dieser Algorithmus ist sehr schnell und leicht zu verstehen.",
  pt: "Este algoritmo é muito rápido e fácil de entender.",
  ru: "Этот алгоритм очень быстрый и простой для понимания.",
  ar: "هذه الخوارزمية سريعة جدًا وسهلة الفهم والاستخدام.",
};

for (const [language, text] of Object.entries(examples)) {
  test(`detects ${language} and selects from the generated catalog`, () => {
    const result = reply(text);
    assert.equal(result.language, language);
    assert.equal(result.text, replyCatalog[language][result.index]);
    assert.notEqual(result.detection.source, "fallback");
    assert.equal(result.detection.requested, "auto");
  });
}

test("all ten language overrides work independently of the input", () => {
  assert.equal(Object.keys(supportedLanguages).length, 10);
  for (const language of Object.keys(supportedLanguages)) {
    const result = reply("hello", { language });
    assert.equal(result.language, language);
    assert.equal(result.detection.source, "override");
    assert.equal(result.text, replyCatalog[language][result.index]);
  }
});

test("common short greetings route without requiring a long paragraph", () => {
  for (const [text, language] of Object.entries({
    "hello!": "en", "Bonjour": "fr", "merci beaucoup": "fr", "Guten Tag": "de",
    "Hola": "es", "¡Hola!": "es", "olá": "pt", "Bom dia": "pt", "你好": "zh",
    "こんにちは": "ja", "안녕": "ko", "Привет": "ru", "مرحبا": "ar",
  })) assert.equal(detectLanguage(text).language, language, text);
});

test("supports Unicode normalization", () => {
  assert.equal(detectLanguage("ｈｅｌｌｏ！").language, "en");
  assert.equal(detectLanguage("ola\u0301").language, "pt");
  assert.equal(detectLanguage("١٢٣٤٥٦٧٨٩٠١٢٣٤٥٦٧٨٩٠ This is nice.").language, "en");
});

test("ambiguous, mixed, or unsupported evidence falls back explicitly", () => {
  for (const text of ["12345", "🤝✨", "?!", "ok", "x", "test", "hello bonjour hola", "你好hello", "नमस्ते"]) {
    const result = reply(text);
    assert.equal(result.language, "en", text);
    assert.equal(result.detection.source, "fallback", text);
  }
});

test("empty, oversize, and invalid inputs produce useful errors", () => {
  for (const text of ["", " ", "\n\t", "\u3000"]) {
    assert.throws(() => reply(text), /non-whitespace/);
  }
  for (const text of [null, undefined, 123, {}, ["hello"]]) {
    assert.throws(() => reply(text), /string/);
  }
  assert.throws(() => reply("a".repeat(maxInputLength + 1)), /at most 8000/);
  for (const language of ["xx", "constructor", "__proto__", "EN", 5]) {
    assert.throws(() => reply("hello", { language }), /Unsupported language/);
  }
  assert.throws(() => reply("hello", null), /Options/);
});

test("rejection sampling discards the biased tail of the Uint32 range", () => {
  const values = [0xffffffff, 0xfffffffe];
  const provider = { getRandomValues(buffer) { buffer[0] = values.shift(); return buffer; } };
  assert.equal(uniformIndex(5, provider), 4);
  assert.equal(values.length, 0, "must reject 2^32 - 1 for a five-element pool");
});

test("sampling handles both boundaries and power-of-two pools", () => {
  const constant = (value) => ({ getRandomValues(buffer) { buffer[0] = value; return buffer; } });
  assert.equal(uniformIndex(5, constant(0)), 0);
  assert.equal(uniformIndex(5, constant(4)), 4);
  assert.equal(uniformIndex(1, constant(0xffffffff)), 0);
  assert.equal(uniformIndex(2 ** 32, constant(0xffffffff)), 0xffffffff);
  for (const size of [0, -1, 1.2, NaN, Infinity, "5", 2 ** 32 + 1]) {
    assert.throws(() => uniformIndex(size), /Pool size/);
  }
  assert.throws(() => uniformIndex(5, null), /Secure randomness/);
  assert.throws(() => uniformIndex(5, {}), /Secure randomness/);
});

test("actual random draws always stay in their language's pool", () => {
  for (const language of Object.keys(supportedLanguages)) {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const result = reply("not persisted", { language });
      assert.equal(result.text, replyCatalog[language][result.index]);
      assert.ok(result.index >= 0 && result.index < replyCatalog[language].length);
      assert.ok(!JSON.stringify(result).includes("not persisted"));
    }
  }
});

test("bundled module is self-contained and has the same public behavior", async () => {
  const bundle = await readFile(new URL("../web/dist/engine.js", import.meta.url), "utf8");
  // A data URL cannot resolve relative/package imports, so this also checks that
  // both the detector and generated replies are included in the deployable file.
  const built = await import(`data:text/javascript;base64,${Buffer.from(bundle).toString("base64")}`);
  assert.deepEqual(built.supportedLanguages, supportedLanguages);
  for (const [language, text] of Object.entries(examples)) {
    const result = built.reply(text);
    assert.equal(result.language, language);
    assert.equal(result.text, replyCatalog[language][result.index]);
  }
  assert.ok(Buffer.byteLength(bundle) < 250_000, "keep the local runtime compact");
  const notices = await readFile(new URL("../web/dist/THIRD_PARTY_NOTICES.txt", import.meta.url), "utf8");
  for (const name of ["franc-min", "trigram-utils", "n-gram", "collapse-white-space"]) {
    assert.ok(notices.includes(name));
  }
});
