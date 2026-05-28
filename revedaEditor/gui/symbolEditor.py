"""Backward compatibility shim - use revedaEditor.gui.symbol_editor instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.symbolEditor' has been renamed to 'revedaEditor.gui.symbol_editor'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.symbol_editor import *  # noqa: F401, F403, E402
