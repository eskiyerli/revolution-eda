"""Backward compatibility shim - use revedaEditor.netlisting.xyce_netlist instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.netlisting.xyceNetlist' has been renamed to 'revedaEditor.netlisting.xyce_netlist'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.netlisting.xyce_netlist import *  # noqa: F401, F403, E402
