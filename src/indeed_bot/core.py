"""Strict subprocess adapter for the compiled Lean response selector.

There is intentionally no Python response bank or substitute selector. The
catalog and every selected response come from the same Lean executable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .detection import SUPPORTED_LANGUAGES

BUILD_GUIDANCE = (
    "Build the verified core from the repository root:\n"
    "  cd lean\n"
    "  lake build\n"
    "Then rerun indeed. For a custom location, set INDEED_CORE to the executable's path."
)


class CoreError(RuntimeError):
    """The verified core is unavailable or violated its transport contract."""


def _find_core(path: str | Path | None = None) -> Path:
    configured = path if path is not None else os.environ.get("INDEED_CORE")
    if configured is not None:
        result = Path(configured).expanduser().resolve()
        if result.is_file() and os.access(result, os.X_OK):
            return result
        raise CoreError(f"Lean core is not an executable file: {result}\n{BUILD_GUIDANCE}")
    # Editable installs work independently of the caller's current directory.
    roots = list(Path(__file__).resolve().parents) + [Path.cwd(), *Path.cwd().parents]
    for root in dict.fromkeys(roots):
        candidate = root / "lean" / ".lake" / "build" / "bin" / "indeed-core"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    installed = shutil.which("indeed-core")
    if installed:
        return Path(installed).resolve()
    raise CoreError(f"The verified Lean core was not found.\n{BUILD_GUIDANCE}")


class LeanCore:
    """Read the catalog and request selections through Lean's JSON protocol."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = _find_core(path)
        raw = self._run("catalog")
        if not isinstance(raw, dict) or set(raw) != set(SUPPORTED_LANGUAGES):
            raise CoreError("Invalid Lean catalog: expected exactly the ten supported locales.")
        for locale, entries in raw.items():
            if not isinstance(entries, list) or not entries or any(
                not isinstance(entry, str) or not entry.strip() for entry in entries
            ):
                raise CoreError(f"Invalid Lean catalog: {locale!r} must have a nonempty string pool.")
        self.catalog: dict[str, tuple[str, ...]] = {
            locale: tuple(entries) for locale, entries in raw.items()
        }

    def _run(self, *arguments: str) -> Any:
        try:
            completed = subprocess.run(
                [str(self.path), *arguments],
                capture_output=True,
                encoding="utf-8",
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            raise CoreError(f"Could not execute the Lean core: {error}") from error
        if completed.returncode:
            # Do not forward unbounded process output; the user's prompt is never
            # sent to this process in the first place.
            detail = completed.stderr.strip()[:300]
            raise CoreError(f"Lean core exited with status {completed.returncode}: {detail or 'no diagnostic'}")
        try:
            return json.loads(completed.stdout)
        except (json.JSONDecodeError, RecursionError) as error:
            raise CoreError("Lean core returned invalid JSON.") from error

    def reply(self, locale: str, draw: int) -> dict[str, Any]:
        """Call the actual verified selector and validate the returned envelope."""
        if locale not in self.catalog:
            raise ValueError(f"Unsupported locale: {locale!r}")
        if isinstance(draw, bool) or not isinstance(draw, int) or draw < 0:
            raise ValueError("draw must be a nonnegative integer")
        value = self._run("reply", locale, str(draw))
        if not isinstance(value, dict):
            raise CoreError("Invalid Lean reply: expected an object.")
        index, size, text = value.get("index"), value.get("pool_size"), value.get("text")
        pool = self.catalog[locale]
        if (
            value.get("locale") != locale
            or type(index) is not int
            or type(size) is not int
            or size != len(pool)
            or not 0 <= index < size
            or index != draw % size
            or not isinstance(text, str)
            or text != pool[index]
        ):
            raise CoreError("Invalid Lean reply: locale, index, text, or pool size disagrees with its catalog.")
        return value
