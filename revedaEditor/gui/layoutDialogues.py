"""Backward compatibility shim - use revedaEditor.gui.layout_dialogues instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.layoutDialogues' has been renamed to 'revedaEditor.gui.layout_dialogues'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.layout_dialogues import *  # noqa: F401, F403, E402
