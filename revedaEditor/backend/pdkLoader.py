"""Backward compatibility shim - use revedaEditor.backend.pdk_loader instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.pdkLoader' has been renamed to 'revedaEditor.backend.pdk_loader'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.pdk_loader import *  # noqa: F401, F403, E402
