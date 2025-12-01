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


from PySide6.QtCore import (
    Signal,
)
from PySide6.QtGui import (
    QPainter,
)
from PySide6.QtPrintSupport import (
    QPrintDialog,
    QPrinter,
)
from PySide6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QGroupBox, QLabel


class revedaPrintDialog(QPrintDialog):
    transparencyChanged = Signal(bool)
    qualityChanged = Signal(str)

    QUALITY_OPTIONS = ["Draft", "Normal", "High"]
    DEFAULT_QUALITY = "Normal"

    def __init__(self, printer=None, parent=None):
        super().__init__(printer or QPrinter(), parent)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI components"""
        # Create options group box
        optionsGroup = QGroupBox("Print Options", self)
        optionsLayout = QGridLayout(optionsGroup)

        # Setup transparency checkbox
        self._setup_transparency(optionsLayout)

        # Setup quality options
        self._setup_quality_options(optionsLayout)

        # Add the options group to the dialog
        self.layout().addWidget(optionsGroup)

    def _setup_transparency(self, layout):
        """Setup transparency checkbox"""
        self.transparentCheck = QCheckBox("Transparent Background")
        self.transparentCheck.setChecked(True)
        # Connect using the clicked signal instead of stateChanged
        self.transparentCheck.clicked.connect(self.transparencyChanged.emit)
        layout.addWidget(self.transparentCheck, 0, 0)

    def _setup_quality_options(self, layout):
        """Setup quality combo box and label"""
        qualityLabel = QLabel("Print Quality:")
        self.qualityCombo = QComboBox()
        self.qualityCombo.addItems(self.QUALITY_OPTIONS)
        self.qualityCombo.setCurrentText(self.DEFAULT_QUALITY)
        self.qualityCombo.currentTextChanged.connect(self.qualityChanged.emit)

        layout.addWidget(qualityLabel, 1, 0)
        layout.addWidget(self.qualityCombo, 1, 1)

    def isTransparent(self):
        """Return whether transparent background is selected"""
        return self.transparentCheck.isChecked()

    def getPrintQuality(self):
        """Return selected print quality"""
        quality_map = {
            "High": QPrinter.HighResolution,
            "Draft": QPrinter.ScreenResolution,
            "Normal": QPrinter.StandardResolution
        }
        return quality_map.get(self.qualityCombo.currentText(), QPrinter.StandardResolution)

    def getRenderHints(self):
        """Return appropriate render hints based on quality setting"""
        current_quality = self.qualityCombo.currentText()
        hints = QPainter.TextAntialiasing

        if current_quality != "Draft":
            hints |= QPainter.Antialiasing | QPainter.SmoothPixmapTransform

        if current_quality == "High":
            hints |= QPainter.HighQualityAntialiasing

        return hints

