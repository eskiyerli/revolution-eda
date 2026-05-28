"""Backward compatibility shim - use revedaEditor.fileio.layout_encoder instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.layoutEncoder' has been renamed to 'revedaEditor.fileio.layout_encoder'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.layout_encoder import *  # noqa: F401, F403, E402
