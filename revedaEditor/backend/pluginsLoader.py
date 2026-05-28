"""Backward compatibility shim - use revedaEditor.backend.plugins_loader instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.pluginsLoader' has been renamed to 'revedaEditor.backend.plugins_loader'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.plugins_loader import *  # noqa: F401, F403, E402
