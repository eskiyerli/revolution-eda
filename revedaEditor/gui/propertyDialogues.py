"""Backward compatibility shim - use revedaEditor.gui.property_dialogues instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.propertyDialogues' has been renamed to 'revedaEditor.gui.property_dialogues'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.property_dialogues import *  # noqa: F401, F403, E402
