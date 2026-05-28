"""Backward compatibility shim - use revedaEditor.fileio.export_gds instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.exportGDS' has been renamed to 'revedaEditor.fileio.export_gds'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.export_gds import *  # noqa: F401, F403, E402
