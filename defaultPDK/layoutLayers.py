"""Backward compatibility shim - use defaultPDK.layout_layers instead."""
import warnings
warnings.warn(
    "Module 'defaultPDK.layoutLayers' has been renamed to 'defaultPDK.layout_layers'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from defaultPDK.layout_layers import *  # noqa: F401, F403, E402
