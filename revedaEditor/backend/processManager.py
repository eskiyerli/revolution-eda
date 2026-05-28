"""Backward compatibility shim - use revedaEditor.backend.process_manager instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.processManager' has been renamed to 'revedaEditor.backend.process_manager'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.process_manager import *  # noqa: F401, F403, E402
