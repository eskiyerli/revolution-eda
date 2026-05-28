"""Backward compatibility shim - use revedaEditor.gui.editor_factory instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.editorFactory' has been renamed to 'revedaEditor.gui.editor_factory'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.editor_factory import *  # noqa: F401, F403, E402
