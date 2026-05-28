"""Backward compatibility shim - use revedaEditor.gui.align_items instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.alignItems' has been renamed to 'revedaEditor.gui.align_items'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.align_items import *  # noqa: F401, F403, E402
