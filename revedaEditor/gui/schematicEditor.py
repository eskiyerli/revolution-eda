"""Backward compatibility shim - use revedaEditor.gui.schematic_editor instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.schematicEditor' has been renamed to 'revedaEditor.gui.schematic_editor'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.schematic_editor import *  # noqa: F401, F403, E402
