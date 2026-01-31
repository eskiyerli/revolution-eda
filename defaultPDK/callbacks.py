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
