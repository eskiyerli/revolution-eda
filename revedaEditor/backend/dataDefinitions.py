"""Backward compatibility shim - use revedaEditor.backend.data_definitions instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.dataDefinitions' has been renamed to 'revedaEditor.backend.data_definitions'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.data_definitions import *  # noqa: F401, F403, E402
