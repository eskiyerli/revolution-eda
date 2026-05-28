"""Backward compatibility shim - use revedaEditor.gui.pdk_registry instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.pdkRegistry' has been renamed to 'revedaEditor.gui.pdk_registry'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.pdk_registry import *  # noqa: F401, F403, E402
