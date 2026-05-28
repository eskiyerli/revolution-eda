"""Backward compatibility shim - use revedaEditor.fileio.import_gds instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.importGDS' has been renamed to 'revedaEditor.fileio.import_gds'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.import_gds import *  # noqa: F401, F403, E402
