"""Backward compatibility shim - use revedaEditor.gui.library_browser instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.libraryBrowser' has been renamed to 'revedaEditor.gui.library_browser'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.library_browser import *  # noqa: F401, F403, E402
