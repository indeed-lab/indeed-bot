"""Public application API: detect, sample a draw, and ask Lean to select."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import random
import secrets
from typing import Any

from .core import LeanCore
from .detection import Detection, detect_language


@dataclass(frozen=True)
class Reply:
    """A selected response and transparent metadata, without the user's prompt."""

    text: str
    language: str
    index: int
    pool_size: int
    detection: Detection

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation of the response metadata."""
        return asdict(self)


class IndeedBot:
    """A local multilingual bot backed by the compiled Lean selector.

    ``seed`` creates reproducible draws within a run; otherwise draws use
    ``secrets.randbelow``. A seed promises repeatability for the same catalog,
    input sequence, detector, and Python implementation, not across all versions.
    """

    def __init__(self, core_path: str | Path | None = None, seed: int | None = None) -> None:
        self.core = LeanCore(core_path)
        generator = random.Random(seed) if seed is not None else None
        self._draw = generator.randrange if generator is not None else secrets.randbelow

    def reply(self, text: str, language: str = "auto") -> Reply:
        """Return one agreement in the detected or explicitly requested language."""
        locale, detection = detect_language(text, language)
        draw = self._draw(len(self.core.catalog[locale]))
        result = self.core.reply(locale, draw)
        return Reply(
            text=result["text"],
            language=result["locale"],
            index=result["index"],
            pool_size=result["pool_size"],
            detection=detection,
        )
