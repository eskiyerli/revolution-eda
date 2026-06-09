# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
##
__author__ = "Revolution Semiconductor"
__copyright__ = "Copyright 2025 Revolution Semiconductor"
__license__ = "Mozilla Public License 2.0"
__version__ = "0.8.1"
__status__ = "Development"
# Import all modules to ensure they're available when used as a plugin
try:
    from . import callbacks
    from . import layoutLayers
    from . import pcells
    from . import process
    from . import schLayers
    from . import symLayers

    __all__ = ['callbacks', 'layoutLayers', 'pcells', 'process', 'schLayers', 'symLayers']
except ImportError as e:
    # Fallback for when modules can't be imported
    __all__ = []
