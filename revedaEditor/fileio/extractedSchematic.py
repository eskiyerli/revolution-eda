"""Backward compatibility shim - use revedaEditor.fileio.extracted_schematic instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.extractedSchematic' has been renamed to 'revedaEditor.fileio.extracted_schematic'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.extracted_schematic import *  # noqa: F401, F403, E402
