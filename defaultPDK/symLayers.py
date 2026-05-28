"""Backward compatibility shim - use defaultPDK.sym_layers instead."""
import warnings
warnings.warn(
    "Module 'defaultPDK.symLayers' has been renamed to 'defaultPDK.sym_layers'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from defaultPDK.sym_layers import *  # noqa: F401, F403, E402
