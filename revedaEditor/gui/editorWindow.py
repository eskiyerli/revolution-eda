"""Backward compatibility shim - use revedaEditor.gui.editor_window instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.editorWindow' has been renamed to 'revedaEditor.gui.editor_window'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.editor_window import *  # noqa: F401, F403, E402
