"""Backward compatibility shim - use revedaEditor.fileio.symbol_encoder instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.symbolEncoder' has been renamed to 'revedaEditor.fileio.symbol_encoder'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.symbol_encoder import *  # noqa: F401, F403, E402
