"""Backward compatibility shim - use revedaEditor.scenes.editor_scene instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.scenes.editorScene' has been renamed to 'revedaEditor.scenes.editor_scene'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.scenes.editor_scene import *  # noqa: F401, F403, E402
