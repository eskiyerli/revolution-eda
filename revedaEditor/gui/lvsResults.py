"""Backward compatibility shim - use revedaEditor.gui.lvs_results instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.gui.lvsResults' has been renamed to 'revedaEditor.gui.lvs_results'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.gui.lvs_results import *  # noqa: F401, F403, E402
