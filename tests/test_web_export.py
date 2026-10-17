"""Keep browser reply data identical to every native selector residue."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("export_web", ROOT / "scripts/export_web.py")
assert SPEC is not None and SPEC.loader is not None
exporter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = exporter
SPEC.loader.exec_module(exporter)


def test_rejects_stale_module_without_rewriting(tmp_path):
    output = tmp_path / "replies.generated.js"
    output.write_text("stale", encoding="utf-8")
    with pytest.raises(exporter.ExportError, match="missing or stale"):
        exporter.check_or_write(output, "fresh", check=True)
    assert output.read_text(encoding="utf-8") == "stale"


def test_rejects_native_catalog_selector_disagreement(monkeypatch):
    def mismatched_core(core, *args):
        if args == ("catalog",):
            return {"en": ["first", "second"]}
        return {"locale": "en", "index": 0, "pool_size": 2, "text": "first"}

    monkeypatch.setattr(exporter, "run_core", mismatched_core)
    with pytest.raises(exporter.ExportError, match=r"en\[1\]"):
        exporter.collect_replies()


@pytest.mark.integration
@pytest.mark.skipif(not exporter.CORE.exists(), reason="Build the Lean core first: cd lean && lake build")
def test_every_generated_reply_matches_native_selector():
    catalog = exporter.collect_replies()
    assert set(catalog) == {"en", "zh", "ja", "ko", "es", "fr", "de", "pt", "ru", "ar"}
    assert all(len(pool) >= 5 for pool in catalog.values())
    source = exporter.OUTPUT.read_text(encoding="utf-8")
    payload = re.search(r"^const replyData = (\{.*?^\});", source, re.MULTILINE | re.DOTALL)
    assert payload is not None
    assert json.loads(payload.group(1)) == catalog
    metadata = exporter.make_metadata(catalog, exporter.source_hashes())
    assert source == exporter.render_module(catalog, metadata)

    # The published checksum is over canonical UTF-8 JSON, not host-specific
    # executable bytes or filesystem paths.
    canonical = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert metadata["catalog_sha256"] == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
