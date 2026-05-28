"""Backward compatibility shim - use revedaEditor.fileio.load_json instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.loadJSON' has been renamed to 'revedaEditor.fileio.load_json'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.load_json import *  # noqa: F401, F403, E402
