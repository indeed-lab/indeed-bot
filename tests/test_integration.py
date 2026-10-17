"""Exercise the shipped Python interface against the real compiled Lean core."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from indeed_bot import IndeedBot, SUPPORTED_LANGUAGES
from indeed_bot.core import LeanCore

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "lean" / ".lake" / "build" / "bin" / "indeed-core"
pytestmark = [pytest.mark.integration, pytest.mark.skipif(not CORE.exists(), reason="Run `cd lean` then `lake build` for core integration tests.")]


@pytest.fixture(scope="module")
def core():
    return LeanCore(CORE)


@pytest.mark.parametrize("locale", SUPPORTED_LANGUAGES)
def test_real_core_boundary_draws(core, locale):
    pool = core.catalog[locale]
    assert len(pool) >= 5
    for draw in [0, len(pool) - 1, len(pool), 10**30 + 17]:
        result = core.reply(locale, draw)
        assert result["index"] == draw % len(pool)
        assert result["text"] == pool[result["index"]]


def test_seeded_reproducibility_and_variety():
    first = IndeedBot(CORE, seed=42)
    second = IndeedBot(CORE, seed=42)
    replies = [first.reply("确实", language="zh") for _ in range(30)]
    assert replies == [second.reply("确实", language="zh") for _ in range(30)]
    assert len({reply.text for reply in replies}) > 1
    assert all(reply.detection.source == "override" for reply in replies)


def test_json_metadata_does_not_include_input():
    reply = IndeedBot(CORE, seed=42).reply("Private prompt: 不保存这个内容", language="zh")
    serialized = reply.to_dict()
    assert set(serialized) == {"text", "language", "index", "pool_size", "detection"}
    assert "Private prompt" not in json.dumps(serialized)
    assert serialized["detection"]["requested"] == "zh"


def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "indeed_bot", *args],
        input=stdin, text=True, capture_output=True, cwd=ROOT, timeout=30,
    )


def test_cli_unicode_json(core):
    result = run_cli("--lang", "zh", "--json", "--seed", "42", "这很有道理")
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert response["language"] == "zh"
    assert response["text"] in core.catalog["zh"]
    assert response["text"] in result.stdout  # readable Unicode, no ASCII escapes


def test_cli_piped_input(core):
    result = run_cli("--lang", "fr", stdin="I want a French response\n")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() in core.catalog["fr"]


def test_cli_interactive_json_lines():
    result = run_cli("--interactive", "--lang", "en", "--json", "--seed", "7", stdin="first\n\nsecond\n/quit\nignored\n")
    assert result.returncode == 0, result.stderr
    values = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(values) == 2
    assert all(value["language"] == "en" for value in values)


def test_cli_empty_input():
    result = run_cli(stdin=" \n")
    assert result.returncode == 2
    assert "non-whitespace" in result.stderr


def test_cli_unknown_language():
    result = run_cli("--lang", "xx", "hello")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
