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
#
# import pdk.layoutLayers as laylyr
from PySide6.QtCore import (
    QPoint,
)

from revedaEditor.backend.pdkLoader import importPDKModule

laylyr = importPDKModule('layoutLayers')
fabproc = importPDKModule('process')
import revedaEditor.common.layoutShapes as lshp


class nmos(lshp.layoutPcell):
    cut = int(0.17 * fabproc.dbu)
    poly_to_cut = int(0.055 * fabproc.dbu)
    diff_ovlp_cut = int(0.06 * fabproc.dbu)
    poly_ovlp_diff = int(0.13 * fabproc.dbu)
    nsdm_ovlp_diff = int(0.12 * fabproc.dbu)
    li_ovlp_cut = int(0.06 * fabproc.dbu)
    sa = poly_to_cut + cut + diff_ovlp_cut
    sd = 2 * (max(poly_to_cut, diff_ovlp_cut)) + cut

    # when initialized it has no shapes.
    def __init__(
            self,
            width: str = 4.0,
            length: str = 0.13,
            nf: str = 1,
    ):
        self._shapes = []
        # define the device parameters here but set them to zero
        self._deviceWidth = float(width)  # device width
        self._drawnWidth: int = int(fabproc.dbu * self._deviceWidth)  # width in grid points
        self._deviceLength = float(length)  # gate length
        self._drawnLength: int = int(fabproc.dbu * self._deviceLength)
        self._nf = int(float(nf))  # number of fingers.
        self._widthPerFinger = int(self._drawnWidth / self._nf)
        super().__init__(self._shapes)

    #

    def __call__(self, width: float, length: float, nf: int):
        '''
        When pcell instance is called, it removes all the shapes and recreates them and adds them as child items to pcell.
        '''
        self._deviceWidth = float(width)  # total gate width
        self._drawnWidth = int(
            self._deviceWidth * fabproc.dbu)  # drawn gate width in grid points
        self._deviceLength = float(length)  # gate length
        self._drawnLength = int(
            self._deviceLength * fabproc.dbu)  # drawn gate length in grid points
        self._nf = int(float(nf))  # number of fingers
        self._widthPerFinger = self._drawnWidth / self._nf
        self.shapes = self.createGeometry()

    def createGeometry(self) -> list[lshp.layoutShape]:
        activeRect = lshp.layoutRect(
            QPoint(0, 0),
            QPoint(
                self._widthPerFinger,
                int(self._nf * self._drawnLength + 2 * nmos.sa + (self._nf - 1) * nmos.sd),
            ),
            laylyr.odLayer_drw,
        )
        polyFingers = [lshp.layoutRect(
            QPoint(-nmos.poly_ovlp_diff,
                   nmos.sa + finger * (self._drawnLength + nmos.sd)),
            QPoint(self._widthPerFinger + nmos.poly_ovlp_diff,
                   nmos.sa + finger * (self._drawnLength + nmos.sd) + self._drawnLength),
            laylyr.poLayer_drw,
        ) for finger in range(self._nf)]
        # contacts = [lshp.layoutRect(

        # )]
        return [activeRect, *polyFingers]

    @property
    def width(self):
        return self._deviceWidth

    @width.setter
    def width(self, value: float):
        self._deviceWidth = value

    @property
    def length(self):
        return self._deviceLength

    @length.setter
    def length(self, value: float):
        self._deviceLength = value

    @property
    def nf(self):
        return self._nf

    @nf.setter
    def nf(self, value: int):
        self._nf = value


class pmos(lshp.layoutPcell):
    pass
