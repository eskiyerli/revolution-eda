"""Backward compatibility shim - use revedaEditor.scenes.symbol_scene instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.scenes.symbolScene' has been renamed to 'revedaEditor.scenes.symbol_scene'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.scenes.symbol_scene import *  # noqa: F401, F403, E402
