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
from quantiphy import Quantity

import revedaEditor.backend.dataDefinitions as ddef
from revedaEditor.backend.pdkLoader import importPDKModule

fabproc = importPDKModule("process")

laylyr = importPDKModule("layoutLayers")

# common process parameters
dbu = 1000  # distance between two points, 1um/1000=1n
snapGrid = 50  # 50nm
majorGrid = 100  # 100nm
layoutScaler = 1e6 * dbu
gdsUnit = Quantity("1 um")
gdsPrecision = Quantity("1 nm")

# Some predefined rules
# via defintions
con = ddef.viaDefTuple(
    "con", laylyr.contactLayer_drw, "", "0.1", "10", "0.1", "10", "0.1", "10"
)
v1 = ddef.viaDefTuple(
    "v1", laylyr.via1Layer_drw, "", "0.2", "10", "0.2", "10", "0.1", "10"
)
processVias = [con, v1]
processViaNames = [item.name for item in processVias]
