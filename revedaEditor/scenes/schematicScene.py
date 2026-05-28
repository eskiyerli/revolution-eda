"""Backward compatibility shim - use revedaEditor.scenes.schematic_scene instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.scenes.schematicScene' has been renamed to 'revedaEditor.scenes.schematic_scene'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.scenes.schematic_scene import *  # noqa: F401, F403, E402
