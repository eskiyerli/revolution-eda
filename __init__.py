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

import pathlib

if pathlib.Path.cwd().joinpath("revinit.py").exists():
    from . import revinit
else:
    print("no revinit file.")
