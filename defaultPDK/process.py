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
snapGrid = 0.05  # 0.05 um
majorGrid = 0.1  # 0.1 um
layoutScaler = 1e6 * dbu
gdsUnit = Quantity("1 um")
gdsPrecision = Quantity("1 nm")

# Some predefined rules
# via defintions
# The optional bottomLayer/topLayer plus enclosure values (in um) let a via
# render its connecting metal layers with enough coverage around the cut.
con = ddef.viaDefTuple(
    "con", laylyr.contactLayer_drw, "", "0.1", "10", "0.1", "10", "0.1", "10",
    bottomLayer=laylyr.activeLayer_drw,
    topLayer=laylyr.m1Layer_drw,
    bottomEnclosure=0.0,
    topEnclosure=0.06,
)
v1 = ddef.viaDefTuple(
    "v1", laylyr.via1Layer_drw, "", "0.2", "10", "0.2", "10", "0.1", "10",
    bottomLayer=laylyr.m1Layer_drw,
    topLayer=laylyr.m2Layer_drw,
    bottomEnclosure=0.06,
    topEnclosure=0.06,
)
processVias = [con, v1]
processViaNames = [item.name for item in processVias]
