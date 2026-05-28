"""Backward compatibility shim - use revedaEditor.backend.library_methods instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.libraryMethods' has been renamed to 'revedaEditor.backend.library_methods'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.library_methods import *  # noqa: F401, F403, E402
