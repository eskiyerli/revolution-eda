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

from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QDoubleValidator,
    QFontDatabase,
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

import revedaEditor.backend.drc_model_view as drcmv
import revedaEditor.common.layout_shapes as lshp
import revedaEditor.gui.edit_functions as edf
from revedaEditor.backend.pdk_loader import importPDKModule

# from dotenv import load_dotenv

process = importPDKModule("process")


class LayoutInstanceDialogue(QDialog):
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
        self.instanceLibName = edf.LongLineEdit()
        self.instanceParamsLayout.addRow("Library:", self.instanceLibName)
        self.instanceCellName = edf.LongLineEdit()
        self.instanceParamsLayout.addRow("Cell:", self.instanceCellName)
        self.instanceViewName = edf.LongLineEdit()
        # self.pinstanceViewName.setReadOnly(True)
        self.instanceParamsLayout.addRow("View:", self.instanceViewName)
        vLayout.addWidget(instanceParamsGroup)

        self.pcellParamsGroup = QGroupBox("Parametric Cell Parameters")
        self.pcellParamsLayout = QFormLayout()
        self.pcellParamsGroup.setLayout(self.pcellParamsLayout)
        vLayout.addWidget(self.pcellParamsGroup)
        self.pcellParamsGroup.hide()

        self.locationGroup = QGroupBox("Location")
        self.locationLayout = QFormLayout()
        self.locationGroup.setLayout(self.locationLayout)
        self.xEdit = edf.ShortLineEdit()
        self.yEdit = edf.ShortLineEdit()
        self.locationLayout.addRow("Location X:", self.xEdit)
        self.locationLayout.addRow("Location Y:", self.yEdit)
        vLayout.addWidget(self.locationGroup)
        self.locationGroup.hide()
        vLayout.addWidget(self.buttonBox)
        self.setLayout(vLayout)
        self.show()


class LayoutInstancePropertiesDialogue(LayoutInstanceDialogue):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("PCell Instance Properties")
        self.instanceNameEdit = edf.LongLineEdit()
        self.instanceParamsLayout.addRow("Instance Name:", self.instanceNameEdit)
        self.locationGroup.show()


class PcellLinkDialogue(QDialog):
    def __init__(self, parent, ViewItem: QStandardItem):
        super().__init__(parent)
        # self.logger = parentW.logger
        self.ViewItem = ViewItem
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
        formLayout.addRow(edf.BoldLabel("PCell:"), self.pcellCB)
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


class CreatePathDialogue(QDialog):
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
        self.formLayout.addRow(edf.BoldLabel("Path Layer:"), self.pathLayerCB)
        self.pathWidth = edf.ShortLineEdit()
        self.pathWidthValidator = QDoubleValidator(self)
        self.pathWidth.setValidator(self.pathWidthValidator)
        self.formLayout.addRow(edf.BoldLabel("Path Width:"), self.pathWidth)
        self.pathNameEdit = edf.ShortLineEdit()
        self.formLayout.addRow(edf.BoldLabel("Path Name:"), self.pathNameEdit)
        self.startExtendEdit = edf.ShortLineEdit()
        self.formLayout.addRow(edf.BoldLabel("Start Extend:"), self.startExtendEdit)
        self.endExtendEdit = edf.ShortLineEdit()
        self.formLayout.addRow(edf.BoldLabel("End Extend:"), self.endExtendEdit)
        mainLayout.addWidget(groupBox)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()


class LayoutPathPropertiesDialog(CreatePathDialogue):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Path Properties")
        # self.mainLayout.removeWidget(self.pathOrientBox)
        self.p1PointEditX = edf.ShortLineEdit()
        self.p1PointEditY = edf.ShortLineEdit()
        self.p2PointEditX = edf.ShortLineEdit()
        self.p2PointEditY = edf.ShortLineEdit()
        self.angleEdit = edf.ShortLineEdit()
        self.formLayout.addRow(edf.BoldLabel("P1 Point X:"), self.p1PointEditX)
        self.formLayout.addRow(edf.BoldLabel("P1 Point Y:"), self.p1PointEditY)
        self.formLayout.addRow(edf.BoldLabel("P2 Point X:"), self.p2PointEditX)
        self.formLayout.addRow(edf.BoldLabel("P2 Point Y:"), self.p2PointEditY)
        self.formLayout.addRow(edf.BoldLabel("Path Angle:"), self.angleEdit)


class CreateLayoutPinDialog(QDialog):
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
        fLayout.addRow(edf.BoldLabel("Pin Name"), self.pinName)
        self.pinDir = QComboBox()
        self.pinDir.addItems(lshp.LayoutPin.pinDirs)
        self.pinDir.setToolTip("Select pin direction")
        fLayout.addRow(edf.BoldLabel("Pin Direction"), self.pinDir)
        self.pinType = QComboBox()
        self.pinType.addItems(lshp.LayoutPin.pinTypes)
        self.pinType.setToolTip("Select pin type")
        fLayout.addRow(edf.BoldLabel("Pin Type"), self.pinType)
        self.mainLayout.addWidget(self.pinPropGroupBox)
        self.layerSelectGroupBox = QGroupBox("Select layers")
        self.layerFormLayout = QFormLayout()
        self.layerSelectGroupBox.setLayout(self.layerFormLayout)
        self.pinLayerCB = QComboBox()
        self.layerFormLayout.addRow(edf.BoldLabel("Pin Layer:"), self.pinLayerCB)
        self.labelLayerCB = QComboBox()
        self.labelLayerText = edf.BoldLabel("Label Layer:")
        self.layerFormLayout.addRow(self.labelLayerText, self.labelLayerCB)
        self.mainLayout.addWidget(self.layerSelectGroupBox)
        labelPropBox = QGroupBox("Label Properties")
        labelPropLayout = QFormLayout()
        labelPropBox.setLayout(labelPropLayout)
        self.familyCB = QComboBox()
        self.familyCB.addItems(fixedFamilies)
        self.familyCB.currentTextChanged.connect(self.familyFontStyles)
        labelPropLayout.addRow(edf.BoldLabel("Font Name"), self.familyCB)
        self.fontStyleCB = QComboBox()
        self.fontStyles = QFontDatabase.styles(fixedFamilies[0])
        self.fontStyleCB.addItems(self.fontStyles)
        self.fontStyleCB.currentTextChanged.connect(self.styleFontSizes)
        labelPropLayout.addRow(edf.BoldLabel("Font Style"), self.fontStyleCB)
        self.labelHeightCB = QComboBox()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(fixedFamilies[0], self.fontStyles[0])
        ]
        self.labelHeightCB.addItems(self.fontSizes)
        labelPropLayout.addRow(edf.BoldLabel("Label Height"), self.labelHeightCB)
        self.labelAlignCB = QComboBox()
        self.labelAlignCB.addItems(lshp.LayoutLabel.LABEL_ALIGNMENTS)
        labelPropLayout.addRow(QLabel("Label Alignment"), self.labelAlignCB)
        self.labelOrientCB = QComboBox()
        self.labelOrientCB.addItems(lshp.LayoutLabel.LABEL_ORIENTS)
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


class LayoutPinProperties(QDialog):
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
        fLayout.addRow(edf.BoldLabel("Pin Name"), self.pinName)
        self.pinDir = QComboBox()
        self.pinDir.addItems(lshp.LayoutPin.pinDirs)
        self.pinDir.setToolTip("Select pin direction")
        fLayout.addRow(edf.BoldLabel("Pin Direction"), self.pinDir)
        self.pinType = QComboBox()
        self.pinType.addItems(lshp.LayoutPin.pinTypes)
        self.pinType.setToolTip("Select pin type")
        fLayout.addRow(edf.BoldLabel("Pin Type"), self.pinType)
        self.pinLayerCB = QComboBox()
        fLayout.addRow(edf.BoldLabel("Pin Layer:"), self.pinLayerCB)
        self.pinBottomLeftX = edf.ShortLineEdit()
        fLayout.addRow(edf.BoldLabel("Pin Bottom Left X:"), self.pinBottomLeftX)
        self.pinBottomLeftY = edf.ShortLineEdit()
        fLayout.addRow(edf.BoldLabel("Pin Bottom Left Y:"), self.pinBottomLeftY)
        self.pinTopRightX = edf.ShortLineEdit()
        fLayout.addRow(edf.BoldLabel("Pin Top Right X:"), self.pinTopRightX)
        self.pinTopRightY = edf.ShortLineEdit()
        fLayout.addRow(edf.BoldLabel("Pin Top Right Y:"), self.pinTopRightY)
        self.mainLayout.addWidget(pinPropGroupBox)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class CreateLayoutLabelDialog(QDialog):
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
        self.labelPropLayout.addRow(edf.BoldLabel("Label Name"), self.labelName)
        self.labelLayerCB = QComboBox()
        self.labelPropLayout.addRow(edf.BoldLabel("Label Layer:"), self.labelLayerCB)
        self.familyCB = QComboBox()
        self.familyCB.addItems(fixedFamilies)
        self.familyCB.currentTextChanged.connect(self.familyFontStyles)
        self.labelPropLayout.addRow(edf.BoldLabel("Font Name"), self.familyCB)
        self.fontStyleCB = QComboBox()
        self.fontStyles = QFontDatabase.styles(fixedFamilies[0])
        self.fontStyleCB.addItems(self.fontStyles)
        self.fontStyleCB.currentTextChanged.connect(self.styleFontSizes)
        self.labelPropLayout.addRow(edf.BoldLabel("Font Style"), self.fontStyleCB)
        self.labelHeightCB = QComboBox()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(fixedFamilies[0], self.fontStyles[0])
        ]
        self.labelHeightCB.addItems(self.fontSizes)
        self.labelPropLayout.addRow(edf.BoldLabel("Label Height"), self.labelHeightCB)
        self.labelAlignCB = QComboBox()
        self.labelAlignCB.addItems(lshp.LayoutLabel.LABEL_ALIGNMENTS)
        self.labelPropLayout.addRow(edf.BoldLabel("Label Alignment"), self.labelAlignCB)
        self.labelOrientCB = QComboBox()
        self.labelOrientCB.addItems(lshp.LayoutLabel.LABEL_ORIENTS)
        self.labelPropLayout.addRow(edf.BoldLabel("Label Orientation"), self.labelOrientCB)
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


class LayoutLabelProperties(CreateLayoutLabelDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Layout Label Properties")
        self.labelTopLeftX = edf.ShortLineEdit()
        self.labelPropLayout.addRow(edf.BoldLabel("Label Top Left X:"), self.labelTopLeftX)
        self.labelTopLeftY = edf.ShortLineEdit()
        self.labelPropLayout.addRow(edf.BoldLabel("Label Top Left Y:"), self.labelTopLeftY)


class CreateLayoutViaDialog(QDialog):
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
        singleViaPropsLayout.addRow(edf.BoldLabel("Via Name"), self.singleViaNamesCB)
        self.singleViaWidthEdit = edf.ShortLineEdit()

        self.singleViaWidthEdit.editingFinished.connect(self.singleViaWidthChanged)
        singleViaPropsLayout.addRow(edf.BoldLabel("Via Width"), self.singleViaWidthEdit)
        self.singleViaHeightEdit = edf.ShortLineEdit()

        self.singleViaHeightEdit.editingFinished.connect(self.singleViaHeightChanged)
        singleViaPropsLayout.addRow(edf.BoldLabel("Via Height"), self.singleViaHeightEdit)
        mainLayout.addWidget(self.singleViaPropsGroup)
        self.arrayViaPropsGroup = QGroupBox("Single Via Properties")
        arrayViaPropsLayout = QFormLayout()
        self.arrayViaPropsGroup.setLayout(arrayViaPropsLayout)
        self.arrayViaNamesCB = QComboBox()

        self.arrayViaNamesCB.currentTextChanged.connect(self.arrayViaNameChanged)
        arrayViaPropsLayout.addRow(edf.BoldLabel("Via Name"), self.arrayViaNamesCB)
        self.arrayViaWidthEdit = edf.ShortLineEdit()

        self.arrayViaWidthEdit.editingFinished.connect(self.arrayViaWidthChanged)
        arrayViaPropsLayout.addRow(edf.BoldLabel("Via Width"), self.arrayViaWidthEdit)
        self.arrayViaHeightEdit = edf.ShortLineEdit()

        self.singleViaHeightEdit.editingFinished.connect(self.arrayViaHeightChanged)
        arrayViaPropsLayout.addRow(edf.BoldLabel("Via Height"), self.arrayViaHeightEdit)
        self.arrayXspacingEdit = edf.ShortLineEdit()
        self.arrayXspacingEdit.editingFinished.connect(
            lambda: self.arrayViaSpacingChanged(self.arrayXspacingEdit)
        )
        arrayViaPropsLayout.addRow(edf.BoldLabel("Column Spacing"), self.arrayXspacingEdit)
        self.arrayYspacingEdit = edf.ShortLineEdit()
        self.arrayYspacingEdit.editingFinished.connect(
            lambda: self.arrayViaSpacingChanged(self.arrayYspacingEdit)
        )
        arrayViaPropsLayout.addRow(edf.BoldLabel("Row Spacing"), self.arrayYspacingEdit)
        self.arrayXNumEdit = edf.ShortLineEdit()
        self.arrayXNumEdit.setText("1")
        arrayViaPropsLayout.addRow(edf.BoldLabel("Number of Columns"), self.arrayXNumEdit)
        self.arrayYNumEdit = edf.ShortLineEdit()
        self.arrayYNumEdit.setText("1")
        arrayViaPropsLayout.addRow(edf.BoldLabel("Number of Rows:"), self.arrayYNumEdit)
        mainLayout.addWidget(self.arrayViaPropsGroup)
        self.arrayViaPropsGroup.hide()
        self.singleViaPropsGroup.show()

        self.viaLocationGroup = QGroupBox("Via Location")
        self.viaLocationLayout = QFormLayout()
        self.viaLocationGroup.setLayout(self.viaLocationLayout)
        self.startXEdit = edf.ShortLineEdit()
        self.viaLocationLayout.addRow(edf.BoldLabel("Start X:"), self.startXEdit)
        self.startYEdit = edf.ShortLineEdit()
        self.viaLocationLayout.addRow(edf.BoldLabel("Start Y:"), self.startYEdit)
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

    def arrayViaNameChanged(self, text: str):
        via = [item for item in process.processVias if item.name == text][0]
        self.arrayViaWidthEdit.setText(str(via.minWidth))
        self.arrayViaHeightEdit.setText(str(via.minWidth))

    def singleViaWidthChanged(self):
        text = self.singleViaWidthEdit.text()
        ViaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.singleViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.singleViaWidthEdit, ViaDefTuple.minWidth, ViaDefTuple.maxWidth
        )

    def singleViaHeightChanged(self):
        text = self.singleViaHeightEdit.text()
        ViaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.singleViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.singleViaHeightEdit, ViaDefTuple.minHeight, ViaDefTuple.maxHeight
        )

    def arrayViaWidthChanged(self):
        text = self.arrayViaWidthEdit.text()
        ViaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.arrayViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.arrayViaWidthEdit, ViaDefTuple.minWidth, ViaDefTuple.maxWidth
        )

    def arrayViaHeightChanged(self):
        text = self.arrayViaHeightEdit.text()
        ViaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.arrayViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text, self.arrayViaHeightEdit, ViaDefTuple.minHeight, ViaDefTuple.maxHeight
        )

    def arrayViaSpacingChanged(self, spaceEditField):
        text = spaceEditField.text()
        ViaDefTuple = [
            item
            for item in process.processVias
            if item.name == self.arrayViaNamesCB.currentText()
        ][0]
        self.validateValue(
            text,
            spaceEditField,
            ViaDefTuple.minSpacing,
            ViaDefTuple.maxSpacing,
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


class LayoutViaProperties(CreateLayoutViaDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Layout Via Properties")

        self.viaLocationGroup.show()
        self.show()


class LayoutRectProperties(QDialog):
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
        self.rectGroupLayout.addRow(edf.BoldLabel("Rectangle Layer:"), self.rectLayerCB)
        self.rectWidthEdit = edf.ShortLineEdit()
        self.rectGroupLayout.addRow(edf.BoldLabel("Width:"), self.rectWidthEdit)
        self.rectHeightEdit = edf.ShortLineEdit()
        self.rectGroupLayout.addRow(edf.BoldLabel("Height:"), self.rectHeightEdit)
        self.topLeftEditX = edf.ShortLineEdit()
        self.rectGroupLayout.addRow(edf.BoldLabel("Top Left X:"), self.topLeftEditX)
        self.topLeftEditY = edf.ShortLineEdit()
        self.rectGroupLayout.addRow(edf.BoldLabel("Top Left Y:"), self.topLeftEditY)
        mainLayout.addWidget(self.rectGroup)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()


class PointsTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Del.", "X", "Y"])
        self.setColumnWidth(0, 8)
        self.setShowGrid(True)
        self.setGridStyle(Qt.PenStyle.SolidLine)


class LayoutPolygonProperties(QDialog):
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
        polygonLayerGroupLayout.addRow(edf.BoldLabel("Layer:"), self.polygonLayerCB)
        mainLayout.addLayout(polygonLayerGroupLayout)
        self.tableWidget = PointsTableWidget(self)
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


class FormDictionary:
    """
    This code defines a utility class FormDictionary that extracts data
    from a Qt form layout and converts it into a Python dictionary.
    """

    def __init__(self, formLayout: QFormLayout):
        self.formLayout = formLayout

    def extractDictFormLayout(self) -> Dict[str, edf.LongLineEdit]:
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


class DrcErrorsDialogue(QDialog):
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
