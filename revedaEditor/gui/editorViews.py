"""Backward compatibility shim - use revedaEditor.gui.editor_views instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.editorViews' has been renamed to 'revedaEditor.gui.editor_views'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.editor_views import *  # noqa: F401, F403, E402
