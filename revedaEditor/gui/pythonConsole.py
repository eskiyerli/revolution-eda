"""Backward compatibility shim - use revedaEditor.gui.python_console instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.pythonConsole' has been renamed to 'revedaEditor.gui.python_console'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.python_console import *  # noqa: F401, F403, E402
