"""Backward compatibility shim - use revedaEditor.gui.help_browser instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.helpBrowser' has been renamed to 'revedaEditor.gui.help_browser'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.help_browser import *  # noqa: F401, F403, E402
