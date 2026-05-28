"""Backward compatibility shim - use revedaEditor.fileio.import_spice instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.importSpice' has been renamed to 'revedaEditor.fileio.import_spice'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.import_spice import *  # noqa: F401, F403, E402
