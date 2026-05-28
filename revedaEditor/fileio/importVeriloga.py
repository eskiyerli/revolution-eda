"""Backward compatibility shim - use revedaEditor.fileio.import_veriloga instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.importVeriloga' has been renamed to 'revedaEditor.fileio.import_veriloga'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.import_veriloga import *  # noqa: F401, F403, E402
