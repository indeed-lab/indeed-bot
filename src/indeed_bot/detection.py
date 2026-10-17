"""Best-effort language routing; this module is outside the Lean proof boundary."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "pt": "Português",
    "ru": "Русский",
    "ar": "العربية",
}


@dataclass(frozen=True)
class Detection:
    """A routing decision, including the reason for an English fallback."""

    requested: str
    source: str
    reason: str


@lru_cache(maxsize=1)
def _detector() -> Any:
    # An explicit language override does not import or load Lingua's models.
    from lingua import Language, LanguageDetectorBuilder

    return LanguageDetectorBuilder.from_languages(
        Language.ENGLISH,
        Language.CHINESE,
        Language.JAPANESE,
        Language.KOREAN,
        Language.SPANISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.PORTUGUESE,
        Language.RUSSIAN,
        Language.ARABIC,
    ).build()


def detect_language(text: str, requested: str = "auto") -> tuple[str, Detection]:
    """Route text to a supported locale without claiming calibrated confidence.

    The detector compares only the ten supported languages. Short, mixed, and
    unsupported-language input can be misclassified; ``requested`` is the escape
    hatch. Relative-score thresholds below are routing heuristics, not accuracy
    guarantees. Input is processed locally and is never persisted here.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("Input must contain non-whitespace text.")
    if requested != "auto":
        if requested not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {requested!r}. Use --languages to see available locales.")
        return requested, Detection(requested, "override", "Language explicitly selected by the caller.")

    letters = [character for character in text if character.isalpha()]
    if not letters:
        return "en", Detection("auto", "fallback", "No alphabetic text; using English.")
    if len(letters) < 3 and all("a" <= letter.lower() <= "z" for letter in letters):
        return "en", Detection("auto", "fallback", "Too little language evidence; using English.")

    scores = _detector().compute_language_confidence_values(text)
    if not scores:
        return "en", Detection("auto", "fallback", "No supported-language match; using English.")
    best = scores[0]
    runner_up = scores[1].value if len(scores) > 1 else 0.0
    if best.value < 0.60 or best.value - runner_up < 0.15:
        return "en", Detection("auto", "fallback", "Ambiguous language evidence; using English.")
    locale = best.language.iso_code_639_1.name.lower()
    if locale not in SUPPORTED_LANGUAGES:
        return "en", Detection("auto", "fallback", "No supported-language match; using English.")
    return locale, Detection("auto", "lingua", "Best supported-language match passed the routing heuristic.")
