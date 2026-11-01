# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

import pathlib

if pathlib.Path.cwd().joinpath("revinit.py").exists():
    from . import revinit
else:
    print("no revinit file.")
