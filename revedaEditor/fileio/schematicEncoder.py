"""Backward compatibility shim - use revedaEditor.fileio.schematic_encoder instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.schematicEncoder' has been renamed to 'revedaEditor.fileio.schematic_encoder'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.schematic_encoder import *  # noqa: F401, F403, E402
