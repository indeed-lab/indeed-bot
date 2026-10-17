"""Indeed-as-a-Service: local language detection, verified agreement selection."""

from .bot import IndeedBot, Reply
from .core import CoreError
from .detection import Detection, SUPPORTED_LANGUAGES

__all__ = ["CoreError", "Detection", "IndeedBot", "Reply", "SUPPORTED_LANGUAGES"]
__version__ = "0.1.0"
