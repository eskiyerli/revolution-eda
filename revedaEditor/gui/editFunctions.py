"""Backward compatibility shim - use revedaEditor.gui.edit_functions instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.editFunctions' has been renamed to 'revedaEditor.gui.edit_functions'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.edit_functions import *  # noqa: F401, F403, E402
