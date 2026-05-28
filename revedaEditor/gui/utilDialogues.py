"""Backward compatibility shim - use revedaEditor.gui.util_dialogues instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.utilDialogues' has been renamed to 'revedaEditor.gui.util_dialogues'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.util_dialogues import *  # noqa: F401, F403, E402
