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
