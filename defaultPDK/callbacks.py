# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

from quantiphy import Quantity


class baseInst():
    def __init__(self, labels_dict: dict):
        self._labelsDict = labels_dict


class res(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)

    def doubleR(self):
        Rvalue = self._labelsDict.get('R').labelValue
        if Rvalue.isalnum():
            return str(2 * Quantity(Rvalue))
        return '?'


class nmos(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
        self.w = Quantity(self._labelsDict['@w'].labelValue)
        self.l = Quantity(self._labelsDict['@l'].labelValue)
        self.nf = Quantity(self._labelsDict['@nf'].labelValue)
        self.sd1p8v = 0.28
        self.sa1p8v = sb1p8v = 0.265
        self.sourceDiffs = lambda nf: int(int(nf) / 2 + 1)

    def asparm(self):
        return self.sourceDiffs(self.nf) * (self.w / self.nf) * self.sd1p8v


class dnwpw(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)


class npolyf_u(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)


class ind(baseInst):
    def __init__(self, labels_dict: dict):
        super().__init__(labels_dict)
