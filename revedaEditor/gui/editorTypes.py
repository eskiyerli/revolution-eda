"""Backward compatibility shim - use revedaEditor.gui.editor_types instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.editorTypes' has been renamed to 'revedaEditor.gui.editor_types'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.editor_types import *  # noqa: F401, F403, E402
