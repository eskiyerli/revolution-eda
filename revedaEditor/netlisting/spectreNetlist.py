"""Backward compatibility shim - use revedaEditor.netlisting.spectre_netlist instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.netlisting.spectreNetlist' has been renamed to 'revedaEditor.netlisting.spectre_netlist'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.netlisting.spectre_netlist import *  # noqa: F401, F403, E402
