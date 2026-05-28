"""Backward compatibility shim - use plugins.aiTerminal.claude_ai_agent instead."""
import warnings
warnings.warn(
    "Module 'plugins.aiTerminal.claudeAiAgent' has been renamed to 'plugins.aiTerminal.claude_ai_agent'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from plugins.aiTerminal.claude_ai_agent import *  # noqa: F401, F403, E402
