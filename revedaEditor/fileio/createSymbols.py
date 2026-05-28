"""Backward compatibility shim - use revedaEditor.fileio.create_symbols instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.createSymbols' has been renamed to 'revedaEditor.fileio.create_symbols'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.create_symbols import *  # noqa: F401, F403, E402
