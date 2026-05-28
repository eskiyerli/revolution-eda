"""Backward compatibility shim - use plugins.aiTerminal.gemini_ai_agent instead."""
import warnings
warnings.warn(
    "Module 'plugins.aiTerminal.geminiAiAgent' has been renamed to 'plugins.aiTerminal.gemini_ai_agent'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from plugins.aiTerminal.gemini_ai_agent import *  # noqa: F401, F403, E402
