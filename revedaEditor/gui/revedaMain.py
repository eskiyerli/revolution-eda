"""Backward compatibility shim - use revedaEditor.gui.reveda_main instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.revedaMain' has been renamed to 'revedaEditor.gui.reveda_main'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.reveda_main import *  # noqa: F401, F403, E402
