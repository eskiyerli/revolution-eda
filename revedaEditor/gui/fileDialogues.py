"""Backward compatibility shim - use revedaEditor.gui.file_dialogues instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.fileDialogues' has been renamed to 'revedaEditor.gui.file_dialogues'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.file_dialogues import *  # noqa: F401, F403, E402
