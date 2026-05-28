"""Backward compatibility shim - use revedaEditor.gui.plugins_registry instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.pluginsRegistry' has been renamed to 'revedaEditor.gui.plugins_registry'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.plugins_registry import *  # noqa: F401, F403, E402
