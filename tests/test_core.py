"""The subprocess boundary rejects malformed or inconsistent core responses."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from indeed_bot.core import CoreError, LeanCore
from indeed_bot.detection import SUPPORTED_LANGUAGES


@pytest.fixture
def catalog():
    return {locale: [f"{locale}: first", f"{locale}: second"] for locale in SUPPORTED_LANGUAGES}


def stub_core(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "protocol-stub"
    path.write_text(f"#!{sys.executable}\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_catalog_is_read_from_subprocess(tmp_path, catalog):
    path = stub_core(tmp_path, f"print({json.dumps(json.dumps(catalog))})")
    core = LeanCore(path)
    assert core.catalog["zh"] == ("zh: first", "zh: second")


@pytest.mark.parametrize(
    "body, message",
    [
        ("print('not json')", "invalid JSON"),
        ("print('{}')", "ten supported locales"),
        ("import sys; sys.exit(7)", "status 7"),
    ],
)
def test_bad_core_process(tmp_path, body, message):
    with pytest.raises(CoreError, match=message):
        LeanCore(stub_core(tmp_path, body))


def test_timeout_is_a_core_error(tmp_path, monkeypatch):
    path = stub_core(tmp_path, "pass")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 10)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(CoreError, match="Could not execute"):
        LeanCore(path)


def test_missing_core_explains_build_command(tmp_path):
    with pytest.raises(CoreError, match="lake build"):
        LeanCore(tmp_path / "does-not-exist")


@pytest.mark.parametrize("bad_pool", [[], [""], ["   "], [4], "wrong type"])
def test_invalid_catalog_pool(tmp_path, catalog, bad_pool):
    catalog["zh"] = bad_pool
    path = stub_core(tmp_path, f"print({json.dumps(json.dumps(catalog))})")
    with pytest.raises(CoreError, match="nonempty string pool"):
        LeanCore(path)


@pytest.mark.parametrize(
    "patch",
    [
        {"locale": "fr"},
        {"index": -1},
        {"index": 2},
        {"index": True},
        {"index": 0, "text": "en: first"},
        {"pool_size": False},
        {"pool_size": 9},
        {"text": "not in the catalog"},
        {"text": None},
    ],
)
def test_reply_envelope_validation(tmp_path, catalog, patch):
    result = {"locale": "en", "index": 1, "text": "en: second", "pool_size": 2} | patch
    path = stub_core(
        tmp_path,
        "import sys\n"
        f"print({json.dumps(json.dumps(catalog))} if sys.argv[1] == 'catalog' else {json.dumps(json.dumps(result))})",
    )
    with pytest.raises(CoreError, match="Invalid Lean reply"):
        LeanCore(path).reply("en", 1)


def test_subprocess_never_receives_prompt(tmp_path, catalog, monkeypatch):
    path = stub_core(tmp_path, f"print({json.dumps(json.dumps(catalog))})")
    core = LeanCore(path)
    arguments = []

    def run(*args, **kwargs):
        arguments.append(args[0])
        return subprocess.CompletedProcess(args[0], 0, json.dumps({
            "locale": "en", "index": 0, "text": "en: first", "pool_size": 2,
        }), "")

    monkeypatch.setattr(subprocess, "run", run)
    assert core.reply("en", 0)["text"] == "en: first"
    assert arguments == [[str(path), "reply", "en", "0"]]


@pytest.mark.parametrize("draw", [-1, True, 1.2, "1"])
def test_invalid_draw_rejected(tmp_path, catalog, draw):
    path = stub_core(tmp_path, f"print({json.dumps(json.dumps(catalog))})")
    with pytest.raises(ValueError, match="nonnegative integer"):
        LeanCore(path).reply("en", draw)


def test_unknown_locale_rejected(tmp_path, catalog):
    path = stub_core(tmp_path, f"print({json.dumps(json.dumps(catalog))})")
    with pytest.raises(ValueError, match="Unsupported locale"):
        LeanCore(path).reply("xx", 0)
