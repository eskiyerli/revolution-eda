"""Backward compatibility shim - use revedaEditor.gui.tools_dialogues instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.toolsDialogues' has been renamed to 'revedaEditor.gui.tools_dialogues'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.tools_dialogues import *  # noqa: F401, F403, E402
