# 
# Revolution EDA
# 
# Copyright (c) 2026 Revolution Semiconductor
#
# This Source Code Form is subject to the terms of the
# Mozilla Public License, v. 2.0.
# If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
from itertools import combinations
from typing import Set

from revedaEditor.common.shapes import schematicSymbol


def checkSymbolOverlaps(symbolSet: Set[schematicSymbol]):
    """
    Checks if any symbol overlaps with other symbols.
    """
    collisionRectSet = set()
    if symbolSet is None:
        return False, collisionRectSet
    symbolSetCombos = combinations(symbolSet, 2)
    if symbolSetCombos is None:
        return False, collisionRectSet
    for symbol1, symbol2 in symbolSetCombos:
        if symbol1.collidesWithItem(symbol2):
            path1 = symbol1.mapToScene(symbol1.shape())
            path2 = symbol2.mapToScene(symbol2.shape())
            collisionPath = path1.intersected(path2)
            if not collisionPath.isEmpty():
                collisionRectSet.add(collisionPath.boundingRect(
                ).toRect())
    return True, collisionRectSet


def checkUnconnectedNets(netSet: Set["schematicNet"]):
    """
    Checks if any net is unconnected.
    """
    netEndSet = set()
    for netItem in netSet:
        netEndSet.update(netItem.sceneEndPoints)
