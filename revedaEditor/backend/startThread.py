"""Backward compatibility shim - use revedaEditor.backend.start_thread instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.startThread' has been renamed to 'revedaEditor.backend.start_thread'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.start_thread import *  # noqa: F401, F403, E402
