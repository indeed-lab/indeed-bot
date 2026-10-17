"""Metadata commands do not require a built core or language-model load."""

import json

from indeed_bot.cli import main


def test_languages_without_core(capsys, monkeypatch):
    monkeypatch.setenv("INDEED_CORE", "/missing/core")
    assert main(["--languages", "--json"]) == 0
    languages = json.loads(capsys.readouterr().out)
    assert len(languages) == 10
    assert languages["zh"] == "中文"


def test_missing_core_is_actionable(capsys, monkeypatch):
    monkeypatch.setenv("INDEED_CORE", "/missing/core")
    assert main(["hello", "--lang", "en"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "lake build" in captured.err
    assert "INDEED_CORE" in captured.err
