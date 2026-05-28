"""Backward compatibility shim - use revedaEditor.backend.library_model_view instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.libraryModelView' has been renamed to 'revedaEditor.backend.library_model_view'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.library_model_view import *  # noqa: F401, F403, E402
