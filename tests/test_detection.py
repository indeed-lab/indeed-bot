"""Routing tests cover real multilingual text and explicit fallback behavior."""

from types import SimpleNamespace

import pytest

from indeed_bot import detection
from indeed_bot.detection import detect_language


@pytest.mark.parametrize(
    "text, locale",
    [
        ("这个算法的运行速度非常快，我觉得我们应该继续优化它。", "zh"),
        ("このアルゴリズムはとても速いので、もっと詳しく調べたいです。", "ja"),
        ("이 알고리즘은 정말 빠르고 사용하기도 편리합니다.", "ko"),
        ("This algorithm is very fast and easy to understand.", "en"),
        ("Este algoritmo es muy rápido y fácil de entender.", "es"),
        ("Cet algorithme est très rapide et facile à comprendre.", "fr"),
        ("Dieser Algorithmus ist sehr schnell und leicht zu verstehen.", "de"),
        ("Este algoritmo é muito rápido e fácil de entender.", "pt"),
        ("Этот алгоритм очень быстрый и простой для понимания.", "ru"),
        ("هذه الخوارزمية سريعة جدًا وسهلة الفهم والاستخدام.", "ar"),
    ],
)
def test_real_language_detection(text, locale):
    detected, info = detect_language(text)
    assert detected == locale
    assert info.source == "lingua"


def test_override_does_not_load_detector(monkeypatch):
    def unexpected():
        raise AssertionError("Explicit overrides should not load language models")

    monkeypatch.setattr(detection, "_detector", unexpected)
    locale, info = detect_language("This message is in English", "ja")
    assert locale == "ja"
    assert info.source == "override"


@pytest.mark.parametrize("text", ["", " ", "\n\t", "\u3000"])
def test_empty_input(text):
    with pytest.raises(ValueError, match="non-whitespace"):
        detect_language(text)


def test_non_string_input():
    with pytest.raises(TypeError, match="string"):
        detect_language(123)


def test_unknown_language():
    with pytest.raises(ValueError, match="Unsupported language"):
        detect_language("hello", "xx")


@pytest.mark.parametrize("text", ["12345", "🤝✨", "?!", "ok", "a"])
def test_insufficient_evidence_falls_back(text):
    locale, info = detect_language(text)
    assert locale == "en"
    assert info.source == "fallback"


def test_ambiguous_scores_fall_back(monkeypatch):
    scores = [SimpleNamespace(value=0.51), SimpleNamespace(value=0.49)]
    monkeypatch.setattr(detection, "_detector", lambda: SimpleNamespace(
        compute_language_confidence_values=lambda _: scores,
    ))
    locale, info = detect_language("ambiguous example")
    assert locale == "en"
    assert info.source == "fallback"
    assert "Ambiguous" in info.reason
