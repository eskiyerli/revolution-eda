"""Backward compatibility shim - use revedaEditor.gui.config_editor instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.configEditor' has been renamed to 'revedaEditor.gui.config_editor'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.config_editor import *  # noqa: F401, F403, E402
