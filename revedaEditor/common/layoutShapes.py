"""Backward compatibility shim - use revedaEditor.common.layout_shapes instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.common.layoutShapes' has been renamed to 'revedaEditor.common.layout_shapes'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.common.layout_shapes import *  # noqa: F401, F403, E402
