"""Backward compatibility shim - use revedaEditor.backend.edit_functions instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.editFunctions' has been renamed to 'revedaEditor.backend.edit_functions'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.edit_functions import *  # noqa: F401, F403, E402
