"""Backward compatibility shim - use revedaEditor.fileio.import_xschem_sym instead."""
import warnings
warnings.warn(
    "Module 'revedaEditor.fileio.importXschemSym' has been renamed to 'revedaEditor.fileio.import_xschem_sym'. "
    "Please update your imports.",
    DeprecationWarning,
    stacklevel=2,
)
from revedaEditor.fileio.import_xschem_sym import *  # noqa: F401, F403, E402
