"""Backward compatibility shim - use revedaEditor.gui.library_registry instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.libraryRegistry' has been renamed to 'revedaEditor.gui.library_registry'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.library_registry import *  # noqa: F401, F403, E402
