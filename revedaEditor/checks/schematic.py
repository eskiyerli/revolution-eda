#    “Commons Clause” License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, “Sell” means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)

from revedaEditor.common.shapes import schematicSymbol
from itertools import combinations, product
from typing import Set


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
