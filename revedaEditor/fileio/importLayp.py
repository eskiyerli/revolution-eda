"""Backward compatibility shim - use revedaEditor.fileio.import_layp instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.importLayp' has been renamed to 'revedaEditor.fileio.import_layp'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.import_layp import *  # noqa: F401, F403, E402
