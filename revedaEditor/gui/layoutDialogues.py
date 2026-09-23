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

from pathlib import Path
from typing import ClassVar, Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QDoubleValidator,
    QFontDatabase,
    QIntValidator,
    QStandardItem,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import revedaEditor.backend.drcModelView as drcmv
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.gui.editFunctions as edf
from revedaEditor.backend.pdkLoader import importPDKModule, lazyPDKModule

# from dotenv import load_dotenv

process = lazyPDKModule("process")


class layoutInstanceDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Layout Instance/Pcell Options")
        self.setMinimumWidth(400)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        vLayout = QVBoxLayout()

        instanceParamsGroup = QGroupBox("Instance Parameters")
        self.instanceParamsLayout = QFormLayout()
        instanceParamsGroup.setLayout(self.instanceParamsLayout)
        self.instanceLibName = edf.longLineEdit()
        self.instanceParamsLayout.addRow("Library:", self.instanceLibName)
        self.instanceCellName = edf.longLineEdit()
        self.instanceParamsLayout.addRow("Cell:", self.instanceCellName)
        self.instanceViewName = edf.longLineEdit()
        # self.pinstanceViewName.setReadOnly(True)
        self.instanceParamsLayout.addRow("View:", self.instanceViewName)
        vLayout.addWidget(instanceParamsGroup)

        self.pcellParamsGroup = QGroupBox("Parametric Cell Parameters")
        self.pcellParamsLayout = QFormLayout()
        self.pcellParamsGroup.setLayout(self.pcellParamsLayout)
        vLayout.addWidget(self.pcellParamsGroup)
        self.pcellParamsGroup.hide()

        # Mosaic: rows x cols copies of the cell spaced by the pitches below
        # (in um). A 1x1 array is a plain placement.
        self.arrayGroup = QGroupBox("Instance Array (Mosaic)")
        self.arrayLayout = QFormLayout()
        self.arrayGroup.setLayout(self.arrayLayout)
        self.rowsEdit = edf.shortLineEdit()
        self.rowsEdit.setValidator(QIntValidator(1, 100000, self))
        self.arrayLayout.addRow(edf.boldLabel("Rows:"), self.rowsEdit)
        self.colsEdit = edf.shortLineEdit()
        self.colsEdit.setValidator(QIntValidator(1, 100000, self))
        self.arrayLayout.addRow(edf.boldLabel("Columns:"), self.colsEdit)
        self.rowPitchEdit = edf.shortLineEdit()
        self.rowPitchEdit.setValidator(QDoubleValidator(0.0, 1e9, 6, self))
        self.arrayLayout.addRow(edf.boldLabel("Row Pitch (um):"), self.rowPitchEdit)
        self.colPitchEdit = edf.shortLineEdit()
        self.colPitchEdit.setValidator(QDoubleValidator(0.0, 1e9, 6, self))
        self.arrayLayout.addRow(edf.boldLabel("Column Pitch (um):"), self.colPitchEdit)
        vLayout.addWidget(self.arrayGroup)
        self.arrayGroup.hide()

        self.locationGroup = QGroupBox("Location")
        self.locationLayout = QFormLayout()
        self.locationGroup.setLayout(self.locationLayout)
        self.xEdit = edf.shortLineEdit()
        self.yEdit = edf.shortLineEdit()
        self.locationLayout.addRow("Location X:", self.xEdit)
        self.locationLayout.addRow("Location Y:", self.yEdit)
        vLayout.addWidget(self.locationGroup)
        self.locationGroup.hide()
        vLayout.addWidget(self.buttonBox)
        self.setLayout(vLayout)
        self.show()

    def arraySpec(self) -> tuple[int, int, float, float] | None:
        """(rows, cols, rowPitch_um, colPitch_um), or None for a 1x1/invalid form."""
        try:
            rows = max(1, int(self.rowsEdit.text() or "1"))
            cols = max(1, int(self.colsEdit.text() or "1"))
        except ValueError:
            return None
        if rows * cols <= 1:
            return None
        try:
            rowPitch = float(self.rowPitchEdit.text())
            colPitch = float(self.colPitchEdit.text())
        except ValueError:
            return None
        return rows, cols, rowPitch, colPitch


class layoutInstancePropertiesDialogue(layoutInstanceDialogue):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("PCell Instance Properties")
        self.instanceNameEdit = edf.longLineEdit()
        self.instanceParamsLayout.addRow("Instance Name:", self.instanceNameEdit)
        self.locationGroup.show()


class pcellLinkDialogue(QDialog):
    def __init__(self, parent, viewItem: QStandardItem):
        super().__init__(parent)
        # self.logger = parentW.logger
        self.viewItem = viewItem
        # self.pcells = self.getClasses()
        self.pcells = list(importPDKModule("pcells").pcells.keys())
        self.setWindowTitle("PCell Settings")
        self.setMinimumSize(400, 200)
        self.mainLayout = QVBoxLayout()
        groupBox = QGroupBox()
        groupLayout = QVBoxLayout()
        formLayout = QFormLayout()
        groupBox.setLayout(groupLayout)
        self.pcellCB = QComboBox()
        self.pcellCB.addItems(self.pcells)
        formLayout.addRow(edf.boldLabel("PCell:"), self.pcellCB)
        groupLayout.addLayout(formLayout)
        self.mainLayout.addWidget(groupBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()

    # @staticmethod
    # def getClasses():
    #     module = importPDKModule('pcells')
    #     return [name for name, obj in inspect.getmembers(module, inspect.isclass)
    #             if issubclass(obj, module.baseCell)]


class createPathDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Create Path")
        # self.setMinimumSize(300, 300)
        mainLayout = QVBoxLayout()
        self.pathOrientBox = QGroupBox("Path Orientation")
        horizontalLayout = QHBoxLayout(self.pathOrientBox)
        self.pathOrientBox.setLayout(horizontalLayout)
        pathOrientGroup = QButtonGroup()
        self.manhattanButton = QRadioButton("Manhattan")
        pathOrientGroup.addButton(self.manhattanButton)
        horizontalLayout.addWidget(self.manhattanButton)
        self.diagonalButton = QRadioButton("Diagonal")
        pathOrientGroup.addButton(self.diagonalButton)
        horizontalLayout.addWidget(self.diagonalButton)
        self.anyButton = QRadioButton("Any")
        pathOrientGroup.addButton(self.anyButton)
        horizontalLayout.addWidget(self.anyButton)
        self.horizontalButton = QRadioButton("Horizontal")
        pathOrientGroup.addButton(self.horizontalButton)
        horizontalLayout.addWidget(self.horizontalButton)
        self.verticalButton = QRadioButton("Vertical")
        pathOrientGroup.addButton(self.verticalButton)
        horizontalLayout.addWidget(self.verticalButton)
        self.manhattanButton.setChecked(True)
        pathOrientGroup.setExclusive(True)
        mainLayout.addWidget(self.pathOrientBox)
        groupBox = QGroupBox()
        self.formLayout = QFormLayout()
        groupBox.setLayout(self.formLayout)
        self.pathLayerCB = QComboBox()
        self.formLayout.addRow(edf.boldLabel("Path Layer:"), self.pathLayerCB)
        self.pathWidth = edf.shortLineEdit()
        self.pathWidthValidator = QDoubleValidator(self)
        self.pathWidth.setValidator(self.pathWidthValidator)
        self.formLayout.addRow(edf.boldLabel("Path Width:"), self.pathWidth)
        self.pathNameEdit = edf.shortLineEdit()
        self.formLayout.addRow(edf.boldLabel("Path Name:"), self.pathNameEdit)
        self.startExtendEdit = edf.shortLineEdit()
        self.formLayout.addRow(edf.boldLabel("Start Extend:"), self.startExtendEdit)
        self.endExtendEdit = edf.shortLineEdit()
        self.formLayout.addRow(edf.boldLabel("End Extend:"), self.endExtendEdit)
        mainLayout.addWidget(groupBox)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()


class layoutPathPropertiesDialog(createPathDialogue):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Path Properties")
        # self.mainLayout.removeWidget(self.pathOrientBox)
        self.p1PointEditX = edf.shortLineEdit()
        self.p1PointEditY = edf.shortLineEdit()
        self.p2PointEditX = edf.shortLineEdit()
        self.p2PointEditY = edf.shortLineEdit()
        self.angleEdit = edf.shortLineEdit()
        self.formLayout.addRow(edf.boldLabel("P1 Point X:"), self.p1PointEditX)
        self.formLayout.addRow(edf.boldLabel("P1 Point Y:"), self.p1PointEditY)
        self.formLayout.addRow(edf.boldLabel("P2 Point X:"), self.p2PointEditX)
        self.formLayout.addRow(edf.boldLabel("P2 Point Y:"), self.p2PointEditY)
        self.formLayout.addRow(edf.boldLabel("Path Angle:"), self.angleEdit)


class createLayoutPinDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Layout Pin")
        self.setMinimumWidth(300)
        fontFamilies = QFontDatabase.families(QFontDatabase.WritingSystem.Latin)
        fixedFamilies = [
            family for family in fontFamilies if QFontDatabase.isFixedPitch(family)
        ]
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.pinPropGroupBox = QGroupBox("Pin Properties")
        fLayout = QFormLayout()
        self.pinPropGroupBox.setLayout(fLayout)
        self.pinName = QLineEdit()
        self.pinName.setPlaceholderText("Pin Name")
        self.pinName.setToolTip("Enter pin name")
        fLayout.addRow(edf.boldLabel("Pin Name"), self.pinName)
        self.pinDir = QComboBox()
        self.pinDir.addItems(lshp.layoutPin.pinDirs)
        self.pinDir.setToolTip("Select pin direction")
        fLayout.addRow(edf.boldLabel("Pin Direction"), self.pinDir)
        self.pinType = QComboBox()
        self.pinType.addItems(lshp.layoutPin.pinTypes)
        self.pinType.setToolTip("Select pin type")
        fLayout.addRow(edf.boldLabel("Pin Type"), self.pinType)
        self.mainLayout.addWidget(self.pinPropGroupBox)
        self.layerSelectGroupBox = QGroupBox("Select layers")
        self.layerFormLayout = QFormLayout()
        self.layerSelectGroupBox.setLayout(self.layerFormLayout)
        self.pinLayerCB = QComboBox()
        self.layerFormLayout.addRow(edf.boldLabel("Pin Layer:"), self.pinLayerCB)
        self.labelLayerCB = QComboBox()
        self.labelLayerText = edf.boldLabel("Label Layer:")
        self.layerFormLayout.addRow(self.labelLayerText, self.labelLayerCB)
        self.mainLayout.addWidget(self.layerSelectGroupBox)
        labelPropBox = QGroupBox("Label Properties")
        labelPropLayout = QFormLayout()
        labelPropBox.setLayout(labelPropLayout)
        self.familyCB = QComboBox()
        self.familyCB.addItems(fixedFamilies)
        self.familyCB.currentTextChanged.connect(self.familyFontStyles)
        labelPropLayout.addRow(edf.boldLabel("Font Name"), self.familyCB)
        self.fontStyleCB = QComboBox()
        self.fontStyles = QFontDatabase.styles(fixedFamilies[0])
        self.fontStyleCB.addItems(self.fontStyles)
        self.fontStyleCB.currentTextChanged.connect(self.styleFontSizes)
        labelPropLayout.addRow(edf.boldLabel("Font Style"), self.fontStyleCB)
        self.labelHeightCB = QComboBox()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(fixedFamilies[0], self.fontStyles[0])
        ]
        self.labelHeightCB.addItems(self.fontSizes)
        labelPropLayout.addRow(edf.boldLabel("Label Height"), self.labelHeightCB)
        self.labelAlignCB = QComboBox()
        self.labelAlignCB.addItems(lshp.layoutLabel.LABEL_ALIGNMENTS)
        labelPropLayout.addRow(QLabel("Label Alignment"), self.labelAlignCB)
        self.labelOrientCB = QComboBox()
        self.labelOrientCB.addItems(lshp.layoutLabel.LABEL_ORIENTS)
        labelPropLayout.addRow(QLabel("Label Orientation"), self.labelOrientCB)
        self.mainLayout.addWidget(labelPropBox)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()

    def familyFontStyles(self, s):
        self.fontStyleCB.clear()
        self.fontStyles = QFontDatabase.styles(self.familyCB.currentText())
        self.fontStyleCB.addItems(self.fontStyles)

    def styleFontSizes(self, s):
        self.labelHeightCB.clear()
        selectedFamily = self.familyCB.currentText()
        selectedStyle = self.fontStyleCB.currentText()
        self.fontSizes = [
            str(size) for size in QFontDatabase.pointSizes(selectedFamily, selectedStyle)
        ]
        self.labelHeightCB.addItems(self.fontSizes)


class layoutPinProperties(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self.setWindowTitle("Layout Pin Properties")
        self.setMinimumWidth(300)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        pinPropGroupBox = QGroupBox("Pin Properties")
        fLayout = QFormLayout()
        pinPropGroupBox.setLayout(fLayout)
        self.pinName = QLineEdit()
        self.pinName.setPlaceholderText("Pin Name")
        self.pinName.setToolTip("Enter pin name")
        fLayout.addRow(edf.boldLabel("Pin Name"), self.pinName)
        self.pinDir = QComboBox()
        self.pinDir.addItems(lshp.layoutPin.pinDirs)
        self.pinDir.setToolTip("Select pin direction")
        fLayout.addRow(edf.boldLabel("Pin Direction"), self.pinDir)
        self.pinType = QComboBox()
        self.pinType.addItems(lshp.layoutPin.pinTypes)
        self.pinType.setToolTip("Select pin type")
        fLayout.addRow(edf.boldLabel("Pin Type"), self.pinType)
        self.pinLayerCB = QComboBox()
        fLayout.addRow(edf.boldLabel("Pin Layer:"), self.pinLayerCB)
        self.pinBottomLeftX = edf.shortLineEdit()
        fLayout.addRow(edf.boldLabel("Pin Bottom Left X:"), self.pinBottomLeftX)
        self.pinBottomLeftY = edf.shortLineEdit()
        fLayout.addRow(edf.boldLabel("Pin Bottom Left Y:"), self.pinBottomLeftY)
        self.pinTopRightX = edf.shortLineEdit()
        fLayout.addRow(edf.boldLabel("Pin Top Right X:"), self.pinTopRightX)
        self.pinTopRightY = edf.shortLineEdit()
        fLayout.addRow(edf.boldLabel("Pin Top Right Y:"), self.pinTopRightY)
        self.mainLayout.addWidget(pinPropGroupBox)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class createLayoutLabelDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Layout Label")
        self.setMinimumWidth(300)
        fontFamilies = QFontDatabase.families(QFontDatabase.WritingSystem.Latin)
        fixedFamilies = [
            family for family in fontFamilies if QFontDatabase.isFixedPitch(family)
        ]
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        labelPropBox = QGroupBox("Label Properties")
        self.labelPropLayout = QFormLayout()
        labelPropBox.setLayout(self.labelPropLayout)
        self.labelName = QLineEdit()
        self.labelName.setPlaceholderText("Label Name")
        self.labelName.setToolTip("Enter label name")
        self.labelPropLayout.addRow(edf.boldLabel("Label Name"), self.labelName)
        self.labelLayerCB = QComboBox()
        self.labelPropLayout.addRow(edf.boldLabel("Label Layer:"), self.labelLayerCB)
        self.familyCB = QComboBox()
        self.familyCB.addItems(fixedFamilies)
        self.familyCB.currentTextChanged.connect(self.familyFontStyles)
        self.labelPropLayout.addRow(edf.boldLabel("Font Name"), self.familyCB)
        self.fontStyleCB = QComboBox()
        self.fontStyles = QFontDatabase.styles(fixedFamilies[0])
        self.fontStyleCB.addItems(self.fontStyles)
        self.fontStyleCB.currentTextChanged.connect(self.styleFontSizes)
        self.labelPropLayout.addRow(edf.boldLabel("Font Style"), self.fontStyleCB)
        self.labelHeightCB = QComboBox()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(fixedFamilies[0], self.fontStyles[0])
        ]
        self.labelHeightCB.addItems(self.fontSizes)
        self.labelPropLayout.addRow(edf.boldLabel("Label Height"), self.labelHeightCB)
        self.labelAlignCB = QComboBox()
        self.labelAlignCB.addItems(lshp.layoutLabel.LABEL_ALIGNMENTS)
        self.labelPropLayout.addRow(edf.boldLabel("Label Alignment"), self.labelAlignCB)
        self.labelOrientCB = QComboBox()
        self.labelOrientCB.addItems(lshp.layoutLabel.LABEL_ORIENTS)
        self.labelPropLayout.addRow(edf.boldLabel("Label Orientation"), self.labelOrientCB)
        self.mainLayout.addWidget(labelPropBox)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()

    def familyFontStyles(self, s):
        self.fontStyleCB.clear()
        self.fontStyles = QFontDatabase.styles(self.familyCB.currentText())
        self.fontStyleCB.addItems(self.fontStyles)

    def styleFontSizes(self, s):
        selectedFamily = self.familyCB.currentText()
        selectedStyle = self.fontStyleCB.currentText()
        self.fontSizes = [
            str(size) for size in QFontDatabase.pointSizes(selectedFamily, selectedStyle)
        ]
        self.labelHeightCB.clear()
        self.labelHeightCB.addItems(self.fontSizes)


class layoutLabelProperties(createLayoutLabelDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Layout Label Properties")
        self.labelTopLeftX = edf.shortLineEdit()
        self.labelPropLayout.addRow(edf.boldLabel("Label Top Left X:"), self.labelTopLeftX)
        self.labelTopLeftY = edf.shortLineEdit()
        self.labelPropLayout.addRow(edf.boldLabel("Label Top Left Y:"), self.labelTopLeftY)


class createLayoutViaDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._parent = parent
        self.setWindowTitle("Create Via(s)")
        self.setMinimumWidth(300)

        mainLayout = QVBoxLayout()
        self.viaTypeGroup = QGroupBox("Via Type")
        self.viaTypeLayout = QHBoxLayout()
        self.singleViaRB = QRadioButton("Single")
        self.singleViaRB.setChecked(True)
        self.singleViaRB.clicked.connect(self.singleViaClicked)
        self.arrayViaRB = QRadioButton("Array")
        self.arrayViaRB.clicked.connect(self.arrayViaClicked)
        self.viaTypeLayout.addWidget(self.singleViaRB)
        self.viaTypeLayout.addWidget(self.arrayViaRB)
        self.viaTypeGroup.setLayout(self.viaTypeLayout)
        mainLayout.addWidget(self.viaTypeGroup)
        self.singleViaPropsGroup = QGroupBox("Single Via Properties")
        singleViaPropsLayout = QFormLayout()
        self.singleViaPropsGroup.setLayout(singleViaPropsLayout)
        self.singleViaNamesCB = QComboBox()
        self.singleViaNamesCB.currentTextChanged.connect(self.singleViaNameChanged)
        singleViaPropsLayout.addRow(edf.boldLabel("Via Name"), self.singleViaNamesCB)
        self.singleViaWidthEdit = edf.shortLineEdit()

        self.singleViaWidthEdit.editingFinished.connect(self.singleViaWidthChanged)
        singleViaPropsLayout.addRow(edf.boldLabel("Via Width"), self.singleViaWidthEdit)
        self.singleViaHeightEdit = edf.shortLineEdit()

        self.singleViaHeightEdit.editingFinished.connect(self.singleViaHeightChanged)
        singleViaPropsLayout.addRow(edf.boldLabel("Via Height"), self.singleViaHeightEdit)
        self.singleBottomEncEdit = edf.shortLineEdit()
        self.singleBottomEncEdit.editingFinished.connect(
            lambda: self.enclosureChanged(self.singleBottomEncEdit, self.singleViaNamesCB, "bottom")
        )
        singleViaPropsLayout.addRow(
            edf.boldLabel("Bottom Enclosure"), self.singleBottomEncEdit
        )
        self.singleTopEncEdit = edf.shortLineEdit()
        self.singleTopEncEdit.editingFinished.connect(
            lambda: self.enclosureChanged(self.singleTopEncEdit, self.singleViaNamesCB, "top")
        )
        singleViaPropsLayout.addRow(
            edf.boldLabel("Top Enclosure"), self.singleTopEncEdit
        )
        mainLayout.addWidget(self.singleViaPropsGroup)
        self.arrayViaPropsGroup = QGroupBox("Single Via Properties")
        arrayViaPropsLayout = QFormLayout()
        self.arrayViaPropsGroup.setLayout(arrayViaPropsLayout)
        self.arrayViaNamesCB = QComboBox()

        self.arrayViaNamesCB.currentTextChanged.connect(self.arrayViaNameChanged)
        arrayViaPropsLayout.addRow(edf.boldLabel("Via Name"), self.arrayViaNamesCB)
        self.arrayViaWidthEdit = edf.shortLineEdit()

        self.arrayViaWidthEdit.editingFinished.connect(self.arrayViaWidthChanged)
        arrayViaPropsLayout.addRow(edf.boldLabel("Via Width"), self.arrayViaWidthEdit)
        self.arrayViaHeightEdit = edf.shortLineEdit()

        self.singleViaHeightEdit.editingFinished.connect(self.arrayViaHeightChanged)
        arrayViaPropsLayout.addRow(edf.boldLabel("Via Height"), self.arrayViaHeightEdit)
        self.arrayBottomEncEdit = edf.shortLineEdit()
        self.arrayBottomEncEdit.editingFinished.connect(
            lambda: self.enclosureChanged(self.arrayBottomEncEdit, self.arrayViaNamesCB, "bottom")
        )
        arrayViaPropsLayout.addRow(
            edf.boldLabel("Bottom Enclosure"), self.arrayBottomEncEdit
        )
        self.arrayTopEncEdit = edf.shortLineEdit()
        self.arrayTopEncEdit.editingFinished.connect(
            lambda: self.enclosureChanged(self.arrayTopEncEdit, self.arrayViaNamesCB, "top")
        )
        arrayViaPropsLayout.addRow(
            edf.boldLabel("Top Enclosure"), self.arrayTopEncEdit
        )
        self.arrayXspacingEdit = edf.shortLineEdit()
        self.arrayXspacingEdit.editingFinished.connect(
            lambda: self.arrayViaSpacingChanged(self.arrayXspacingEdit)
        )
        arrayViaPropsLayout.addRow(edf.boldLabel("Column Spacing"), self.arrayXspacingEdit)
        self.arrayYspacingEdit = edf.shortLineEdit()
        self.arrayYspacingEdit.editingFinished.connect(
            lambda: self.arrayViaSpacingChanged(self.arrayYspacingEdit)
        )
        arrayViaPropsLayout.addRow(edf.boldLabel("Row Spacing"), self.arrayYspacingEdit)
        self.arrayXNumEdit = edf.shortLineEdit()
        self.arrayXNumEdit.setText("1")
        arrayViaPropsLayout.addRow(edf.boldLabel("Number of Columns"), self.arrayXNumEdit)
        self.arrayYNumEdit = edf.shortLineEdit()
        self.arrayYNumEdit.setText("1")
        arrayViaPropsLayout.addRow(edf.boldLabel("Number of Rows:"), self.arrayYNumEdit)
        mainLayout.addWidget(self.arrayViaPropsGroup)
        self.arrayViaPropsGroup.hide()
        self.singleViaPropsGroup.show()

        self.viaLocationGroup = QGroupBox("Via Location")
        self.viaLocationLayout = QFormLayout()
        self.viaLocationGroup.setLayout(self.viaLocationLayout)
        self.startXEdit = edf.shortLineEdit()
        self.viaLocationLayout.addRow(edf.boldLabel("Start X:"), self.startXEdit)
        self.startYEdit = edf.shortLineEdit()
        self.viaLocationLayout.addRow(edf.boldLabel("Start Y:"), self.startYEdit)
        mainLayout.addWidget(self.viaLocationGroup)
        self.viaLocationGroup.hide()

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def singleViaClicked(self):
        self.arrayViaPropsGroup.hide()
        self.singleViaPropsGroup.show()
        self.adjustSize()

    def arrayViaClicked(self):
        self.singleViaPropsGroup.hide()
        self.arrayViaPropsGroup.show()
        self.adjustSize()

    def singleViaNameChanged(self, text: str):
        via = [item for item in process.processVias if item.name == text][0]
        self.singleViaWidthEdit.setText(str(via.minWidth))
        self.singleViaHeightEdit.setText(str(via.minHeight))
        self.singleBottomEncEdit.setText(str(getattr(via, "bottomEnclosure", 0.0)))
        self.singleTopEncEdit.setText(str(getattr(via, "topEnclosure", 0.0)))

    def arrayViaNameChanged(self, text: str):
        via = [item for item in process.processVias if item.name == text][0]
        self.arrayViaWidthEdit.setText(str(via.minWidth))
        self.arrayViaHeightEdit.setText(str(via.minHeight))
        self.arrayBottomEncEdit.setText(str(getattr(via, "bottomEnclosure", 0.0)))
        self.arrayTopEncEdit.setText(str(getattr(via, "topEnclosure", 0.0)))

    def enclosureChanged(self, encEditField, viaNamesCB, side: str):
        """Validate a metal-enclosure entry: it must be a number no smaller than
        the via definition's minimum enclosure for that side. Larger values
        (extra coverage) are allowed."""
        viaDefTuple = [
            item
            for item in process.processVias
            if item.name == viaNamesCB.currentText()
        ][0]
        minEnc = getattr(
            viaDefTuple, "bottomEnclosure" if side == "bottom" else "topEnclosure", 0.0
        )
        text = encEditField.text().strip()
        if not text:
            encEditField.setText(str(minEnc))
            return
        try:
            value = float(text)
            if value < minEnc:
                self._parent.logger.warning(
                    f"Enclosure below minimum, set back to {minEnc}"
                )
                encEditField.setText(str(minEnc))
        except ValueError:
            self._parent.logger.warning(f"Invalid number format, set back to {minEnc}")
            encEditField.setText(str(minEnc))

    def singleViaWidthChanged(self):
        text = self.singleViaWidthEdit.text()
        viaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.singleViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.singleViaWidthEdit, viaDefTuple.minWidth, viaDefTuple.maxWidth
        )

    def singleViaHeightChanged(self):
        text = self.singleViaHeightEdit.text()
        viaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.singleViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.singleViaHeightEdit, viaDefTuple.minHeight, viaDefTuple.maxHeight
        )

    def arrayViaWidthChanged(self):
        text = self.arrayViaWidthEdit.text()
        viaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.arrayViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.arrayViaWidthEdit, viaDefTuple.minWidth, viaDefTuple.maxWidth
        )

    def arrayViaHeightChanged(self):
        text = self.arrayViaHeightEdit.text()
        viaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.arrayViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.arrayViaHeightEdit, viaDefTuple.minHeight, viaDefTuple.maxHeight
        )

    def arrayViaSpacingChanged(self, spaceEditField):
        text = spaceEditField.text()
        viaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.arrayViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text,
            spaceEditField,
            viaDefTuple.minSpacing,
            viaDefTuple.maxSpacing,
        )

    def validateValue(self, text: str, lineEdit: QLineEdit, min_val: float, max_val: float):
        if not text:
            lineEdit.setText(str(min_val))
            return

        try:
            value = float(text)
            if value < min_val:
                self._parent.logger.warning(f"Value too small, set back to {min_val}")
                lineEdit.setText(str(min_val))
            elif value > max_val:
                self._parent.logger.warning(f"Value too large, set back to {max_val}")
                lineEdit.setText(str(max_val))
        except ValueError:
            self._parent.logger.warning(f"Invalid number format, set back to {min_val}")
            lineEdit.setText(str(min_val))


class layoutViaProperties(createLayoutViaDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Layout Via Properties")

        self.viaLocationGroup.show()
        self.show()


class layoutRectProperties(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Layout Rectangle Properties")
        self.setMinimumWidth(300)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout = QVBoxLayout()
        self.rectGroup = QGroupBox("Rectangle Properties")
        self.rectGroupLayout = QFormLayout()
        self.rectGroup.setLayout(self.rectGroupLayout)
        self.rectLayerCB = QComboBox()
        self.rectGroupLayout.addRow(edf.boldLabel("Rectangle Layer:"), self.rectLayerCB)
        self.rectWidthEdit = edf.shortLineEdit()
        self.rectGroupLayout.addRow(edf.boldLabel("Width:"), self.rectWidthEdit)
        self.rectHeightEdit = edf.shortLineEdit()
        self.rectGroupLayout.addRow(edf.boldLabel("Height:"), self.rectHeightEdit)
        self.topLeftEditX = edf.shortLineEdit()
        self.rectGroupLayout.addRow(edf.boldLabel("Top Left X:"), self.topLeftEditX)
        self.topLeftEditY = edf.shortLineEdit()
        self.rectGroupLayout.addRow(edf.boldLabel("Top Left Y:"), self.topLeftEditY)
        mainLayout.addWidget(self.rectGroup)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()


class pointsTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Del.", "X", "Y"])
        self.setColumnWidth(0, 8)
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)


class layoutPolygonProperties(QDialog):
    def __init__(self, parent: QWidget, tupleList: list):
        super().__init__(parent)
        self.tupleList = tupleList
        self.setWindowTitle("Layout Polygon Properties")
        self.setMinimumWidth(300)
        self.setMinimumHeight(400)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        polygonLayerGroup = QGroupBox("Polygon Layer")
        polygonLayerGroupLayout = QFormLayout()
        self.polygonLayerCB = QComboBox()
        polygonLayerGroupLayout.addRow(edf.boldLabel("Layer:"), self.polygonLayerCB)
        mainLayout.addLayout(polygonLayerGroupLayout)
        self.tableWidget = pointsTableWidget(self)
        mainLayout.addWidget(self.tableWidget)
        mainLayout.addWidget(self.buttonBox)

        self.populateTable()

    def populateTable(self):
        self.tableWidget.setRowCount(len(self.tupleList) + 1)  # Add one extra row

        for row, item in enumerate(self.tupleList):
            self.addRow(row, item)

        # Add an empty row at the end
        self.addEmptyRow(len(self.tupleList))

        # Connect cellChanged signal to handle when the last row is edited
        self.tableWidget.cellChanged.connect(self.handleCellChange)

    def addRow(self, row, item):
        delete_checkbox = QCheckBox()
        self.tableWidget.setCellWidget(row, 0, delete_checkbox)

        self.tableWidget.setItem(row, 1, QTableWidgetItem(str(item[0])))
        self.tableWidget.setItem(row, 2, QTableWidgetItem(str(item[1])))
        delete_checkbox.stateChanged.connect(lambda state, r=row: self.deleteRow(r, state))

    def addEmptyRow(self, row):
        # self.table_widget.insertRow(row)
        delete_checkbox = QCheckBox()
        self.tableWidget.setCellWidget(row, 0, delete_checkbox)
        delete_checkbox.stateChanged.connect(lambda state, r=row: self.deleteRow(r, state))

        self.tableWidget.setItem(row, 1, QTableWidgetItem(""))
        self.tableWidget.setItem(row, 2, QTableWidgetItem(""))

    def handleCellChange(self, row, column):
        if (
            row == self.tableWidget.rowCount() - 1
        ):  # Check if last row and tuple text column
            item1 = self.tableWidget.item(row, 1)
            item2 = self.tableWidget.item(row, 2)
            if item1 is not None and item2 is not None:
                text1 = item1.text()
                text2 = item2.text()
                if text1 != "" and text2 != "":
                    self.tableWidget.insertRow(row + 1)
                    self.addEmptyRow(row + 1)

    def deleteRow(self, row, state):
        # print("delete")
        if state == 2:  # Checked state
            self.tableWidget.removeRow(row)


class formDictionary:
    """
    This code defines a utility class formDictionary that extracts data
    from a Qt form layout and converts it into a Python dictionary.
    """

    def __init__(self, formLayout: QFormLayout):
        self.formLayout = formLayout

    def extractDictFormLayout(self) -> Dict[str, edf.longLineEdit]:
        data = {}
        for row in range(self.formLayout.rowCount()):
            labelItem = self.formLayout.itemAt(row, QFormLayout.ItemRole.LabelRole)
            fieldItem = self.formLayout.itemAt(row, QFormLayout.ItemRole.FieldRole)

            if labelItem and fieldItem:
                label = labelItem.widget()
                field = fieldItem.widget()

                if isinstance(label, QLabel) and isinstance(field, QLineEdit):
                    key = label.text().rstrip(":")  # Remove trailing colon if present
                    value = field
                    data[key] = value
        return data


class createMultipartDialogue(QDialog):
    """Pick a multipart kind and its parameters before the two-click draw.

    ``selectedSpec`` returns ``(kind, params)`` with dimensions converted to
    scene units (dbu); the geometry anchors are placeholders the draw flow
    fills in on the second click. ``initialSpec`` lets F3 reopen the form for
    an active multipart placement without discarding its current settings.
    """

    # kind -> [(paramKey, label, default, kindOfField)]
    # kindOfField: "layer" (combo of PDK layers), "via" (combo of process
    # vias + blank), "um" (float, converted x dbu), "int", "str".
    FIELDS: ClassVar[dict] = {
        "guardRing": [
            ("layer", "Ring Layer:", "", "layer"),
            ("width", "Ring Width (um):", "0.3", "um"),
            ("via", "Stitch Via:", "", "via"),
        ],
        "shieldedPath": [
            ("signalLayer", "Signal Layer:", "", "layer"),
            ("signalWidth", "Signal Width (um):", "0.2", "um"),
            ("shieldLayer", "Shield Layer:", "", "layer"),
            ("shieldWidth", "Shield Width (um):", "0.2", "um"),
            ("gap", "Gap (um):", "0.2", "um"),
        ],
        "busRoute": [
            ("layer", "Layer:", "", "layer"),
            ("width", "Width (um):", "0.2", "um"),
            ("spacing", "Spacing (um):", "0.2", "um"),
            ("count", "Count:", "4", "int"),
        ],
    }
    KIND_LABELS: ClassVar[dict] = {
        "guardRing": "Guard Ring",
        "shieldedPath": "Shielded Path",
        "busRoute": "Bus Route",
    }

    def __init__(self, parent, initialSpec: tuple[str, dict] | None = None):
        super().__init__(parent)
        self._initialSpec = initialSpec
        self.setWindowTitle("Create Multipart")
        self.setMinimumWidth(420)
        mainLayout = QVBoxLayout()
        groupBox = QGroupBox()
        self.formLayout = QFormLayout()
        groupBox.setLayout(self.formLayout)
        self.kindCB = QComboBox()
        for kind, label in self.KIND_LABELS.items():
            self.kindCB.addItem(label, kind)
        self.formLayout.addRow(edf.boldLabel("Kind:"), self.kindCB)
        self._fieldWidgets = {}
        mainLayout.addWidget(groupBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        _laylyr = importPDKModule("layoutLayers")
        self._layerNames = [
            layer.name for layer in (_laylyr.pdkAllLayers if _laylyr else [])
        ]
        self.kindCB.currentIndexChanged.connect(self._rebuildFields)
        self._rebuildFields(0)
        if self._initialSpec is not None:
            self.setInitialSpec(*self._initialSpec)
        self.show()

    def setInitialSpec(self, kind: str, params: dict) -> None:
        """Populate this form from an active placement specification."""
        index = self.kindCB.findData(kind)
        if index < 0:
            return
        self.kindCB.setCurrentIndex(index)
        dbu = getattr(process, "dbu", 1000)
        for key, (widget, fieldKind) in self._fieldWidgets.items():
            if key not in params:
                continue
            value = params[key]
            if fieldKind in ("layer", "via"):
                widget.setCurrentText(str(value))
            elif fieldKind == "um":
                widget.setText(f"{float(value) / dbu:g}")
            else:
                widget.setText(str(value))

    def _clearFields(self):
        while self.formLayout.rowCount() > 1:
            self.formLayout.removeRow(1)
        self._fieldWidgets = {}

    def _rebuildFields(self, index):
        self._clearFields()
        kind = self.kindCB.itemData(index)
        for key, label, default, fieldKind in self.FIELDS[kind]:
            if fieldKind == "layer":
                widget = QComboBox()
                widget.addItems(self._layerNames)
            elif fieldKind == "via":
                widget = QComboBox()
                widget.addItem("")
                if process:
                    widget.addItems(
                        getattr(process, "processViaNames", []))
            else:
                widget = edf.shortLineEdit()
                widget.setText(default)
                if fieldKind == "um":
                    widget.setValidator(QDoubleValidator(0.0, 1e9, 6, self))
                elif fieldKind == "int":
                    widget.setValidator(QIntValidator(1, 10000, self))
            self.formLayout.addRow(edf.boldLabel(label), widget)
            self._fieldWidgets[key] = (widget, fieldKind)

    def selectedSpec(self):
        kind = self.kindCB.itemData(self.kindCB.currentIndex())
        dbu = getattr(process, "dbu", 1000)
        params = {}
        for key, (widget, fieldKind) in self._fieldWidgets.items():
            if fieldKind in ("layer", "via"):
                params[key] = widget.currentText()
            elif fieldKind == "um":
                try:
                    params[key] = float(widget.text()) * dbu
                except ValueError:
                    params[key] = 0.0
            elif fieldKind == "int":
                try:
                    params[key] = int(widget.text())
                except ValueError:
                    params[key] = 1
            else:
                params[key] = widget.text()
        # Geometry anchors: the two-click draw writes the real extents.
        if kind == "guardRing":
            params.setdefault("tl", [0, 0])
            params.setdefault("br", [0, 0])
        else:
            params.setdefault("p1", [0, 0])
            params.setdefault("p2", [0, 0])
        return kind, params


class makeCellDialogue(QDialog):
    """Ask for the library and cell name used by Edit > Make Cell."""

    def __init__(self, parent, libraries):
        super().__init__(parent)
        self.setWindowTitle("Make Cell From Selection")
        mainLayout = QVBoxLayout()
        groupBox = QGroupBox()
        formLayout = QFormLayout()
        groupBox.setLayout(formLayout)
        self.libNameCB = QComboBox()
        self.libNameCB.setEditable(True)
        self.libNameCB.addItems(libraries)
        formLayout.addRow(edf.boldLabel("Library:"), self.libNameCB)
        self.cellNameEdit = edf.longLineEdit()
        formLayout.addRow(edf.boldLabel("Cell Name:"), self.cellNameEdit)
        mainLayout.addWidget(groupBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    @property
    def libName(self) -> str:
        return self.libNameCB.currentText().strip()

    @property
    def cellName(self) -> str:
        return self.cellNameEdit.text().strip()


class multipartPropertiesDialogue(QDialog):
    """Generic key->value editor for a multipart item's ``params`` dict.

    Numeric strings parse back as numbers and ``x,y`` pairs as point lists,
    so geometry anchors stay round-trippable through plain text."""

    def __init__(self, parent, item):
        super().__init__(parent)
        self.setWindowTitle(f"{item.kind} Properties")
        self._item = item
        mainLayout = QVBoxLayout()
        groupBox = QGroupBox(f"Kind: {item.kind}")
        self.formLayout = QFormLayout()
        groupBox.setLayout(self.formLayout)
        self._edits = {}
        for key, value in item.params.items():
            edit = edf.longLineEdit()
            if isinstance(value, (list, tuple)):
                edit.setText(",".join(str(v) for v in value))
            else:
                edit.setText(str(value))
            self.formLayout.addRow(edf.boldLabel(f"{key}:"), edit)
            self._edits[key] = edit
        mainLayout.addWidget(groupBox)
        hint = QLabel(
            "Dimensions are in scene units (dbu); point params are 'x,y'.")
        hint.setWordWrap(True)
        mainLayout.addWidget(hint)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def parsedParams(self) -> dict:
        params = {}
        for key, edit in self._edits.items():
            text = edit.text().strip()
            original = self._item.params.get(key)
            if isinstance(original, (list, tuple)):
                try:
                    params[key] = [
                        float(part) for part in text.split(",") if part != ""
                    ]
                    continue
                except ValueError:
                    pass
            try:
                params[key] = int(text)
                continue
            except ValueError:
                pass
            try:
                params[key] = float(text)
                continue
            except ValueError:
                pass
            params[key] = text
        return params


class layerOpDialogue(QDialog):
    """Pick a boolean/size operation for the selected shapes.

    ``selectedOp``/``selectedAmount`` are read after ``exec_``; the amount is
    in layout units (um) and only meaningful for grow/shrink.
    """

    OPS = (
        ("Or (Union)", "or"),
        ("And (Intersect)", "and"),
        ("Xor", "xor"),
        ("Not (A minus other layers)", "not"),
        ("Grow", "grow"),
        ("Shrink", "shrink"),
    )

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Layer Operations")
        mainLayout = QVBoxLayout()
        groupBox = QGroupBox()
        formLayout = QFormLayout()
        groupBox.setLayout(formLayout)
        self.opCB = QComboBox()
        for label, _op in self.OPS:
            self.opCB.addItem(label)
        formLayout.addRow(edf.boldLabel("Operation:"), self.opCB)
        self.amountEdit = edf.shortLineEdit()
        self.amountEdit.setValidator(QDoubleValidator(0.0, 1e6, 6, self))
        self.amountEdit.setText("0.1")
        formLayout.addRow(edf.boldLabel("Amount (um):"), self.amountEdit)
        mainLayout.addWidget(groupBox)

        def opChanged(index):
            self.amountEdit.setEnabled(self.OPS[index][1] in ("grow", "shrink"))

        self.opCB.currentIndexChanged.connect(opChanged)
        opChanged(0)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    @property
    def selectedOp(self) -> str:
        return self.OPS[self.opCB.currentIndex()][1]

    @property
    def selectedAmount(self) -> float:
        try:
            return float(self.amountEdit.text())
        except ValueError:
            return 0.0


class drcErrorsDialogue(QDialog):
    def __init__(self, parent, drcDataPathObj: Path):
        super().__init__(parent)
        self.setWindowTitle("DRC Errors Table")
        self.setMinimumSize(1200, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)

        layout = QVBoxLayout()

        # Add DRC table view
        import revedaEditor.fileio.importlyrdb as imlyrdb

        DRCDataObj = imlyrdb.DRCOutput(str(drcDataPathObj))
        DRCDataObj.parseDRCOutput()
        self.drcTable = drcmv.DRCTableView(
            DRCDataObj.result["violations"], DRCDataObj.result["categories"]
        )
        layout.addWidget(self.drcTable)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)
        self.finished.connect(self._clearDRCPolygons)

        # Connect signal for polygon highlighting
        # self.drcTable.polygonSelected.connect(self.highlightPolygons)

    def _clearDRCPolygons(self, _result: int = 0):
        parent = self.parent()
        clearDRCPolygons = getattr(parent, "clearDRCPolygons", None)
        if callable(clearDRCPolygons):
            clearDRCPolygons()

    def closeEvent(self, event):
        self._clearDRCPolygons()
        super().closeEvent(event)

    # def highlightPolygons(self, polygons):
    #     # Emit signal or call parentW method to highlight polygons in scene
    #     if hasattr(self.parentW(), 'highlightDRCPolygons'):
    #         self.parentW().highlightDRCPolygons(polygons)
