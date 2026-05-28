"""Backward compatibility shim - use revedaEditor.backend.drc_model_view instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.drcModelView' has been renamed to 'revedaEditor.backend.drc_model_view'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.drc_model_view import *  # noqa: F401, F403, E402
