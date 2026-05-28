"""Backward compatibility shim - use revedaEditor.gui.stipple_editor instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.stippleEditor' has been renamed to 'revedaEditor.gui.stipple_editor'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.stipple_editor import *  # noqa: F401, F403, E402
