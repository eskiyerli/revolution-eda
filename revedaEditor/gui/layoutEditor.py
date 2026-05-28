"""Backward compatibility shim - use revedaEditor.gui.layout_editor instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.layoutEditor' has been renamed to 'revedaEditor.gui.layout_editor'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.layout_editor import *  # noqa: F401, F403, E402
