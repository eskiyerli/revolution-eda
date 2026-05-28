"""Backward compatibility shim - use defaultPDK.sch_layers instead."""
import warnings
warnings.warn(
    "Module 'defaultPDK.schLayers' has been renamed to 'defaultPDK.sch_layers'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from defaultPDK.sch_layers import *  # noqa: F401, F403, E402
