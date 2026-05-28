"""Backward compatibility shim - use revedaEditor.backend.undo_stack instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.undoStack' has been renamed to 'revedaEditor.backend.undo_stack'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.undo_stack import *  # noqa: F401, F403, E402
