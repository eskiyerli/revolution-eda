"""Backward compatibility shim - use revedaEditor.backend.hdl_back_end instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.backend.hdlBackEnd' has been renamed to 'revedaEditor.backend.hdl_back_end'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.backend.hdl_back_end import *  # noqa: F401, F403, E402
