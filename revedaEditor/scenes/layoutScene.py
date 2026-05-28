"""Backward compatibility shim - use revedaEditor.scenes.layout_scene instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.scenes.layoutScene' has been renamed to 'revedaEditor.scenes.layout_scene'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.scenes.layout_scene import *  # noqa: F401, F403, E402
