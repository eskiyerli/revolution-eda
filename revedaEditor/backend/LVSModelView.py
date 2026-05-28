"""Backward compatibility shim - use revedaEditor.backend.lvs_model_view instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.LVSModelView' has been renamed to 'revedaEditor.backend.lvs_model_view'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.lvs_model_view import *  # noqa: F401, F403, E402
