"""Backward compatibility shim - use revedaEditor.gui.text_editor instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.textEditor' has been renamed to 'revedaEditor.gui.text_editor'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.text_editor import *  # noqa: F401, F403, E402
