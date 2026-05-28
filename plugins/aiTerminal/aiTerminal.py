"""Backward compatibility shim - use plugins.aiTerminal.ai_terminal instead."""
import warnings
warnings.warn(
    "Module 'plugins.aiTerminal.aiTerminal' has been renamed to 'plugins.aiTerminal.ai_terminal'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from plugins.aiTerminal.ai_terminal import *  # noqa: F401, F403, E402
