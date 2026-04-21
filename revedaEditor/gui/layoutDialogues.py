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
from collections import Counter, defaultdict
from typing import Dict, TYPE_CHECKING

from PySide6.QtCore import Qt, QRect

from PySide6.QtGui import (
    QBrush,
    QColor,
    QDoubleValidator,
    QFontDatabase,
    QPen,
    QStandardItem,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QWidget,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
)

import revedaEditor.backend.drcModelView as drcmv
import revedaEditor.backend.LVSModelView as lvsmv
import revedaEditor.common.layoutShapes as lshp
import revedaEditor.gui.editFunctions as edf
from revedaEditor.backend.pdkLoader import importPDKModule

# from dotenv import load_dotenv

process = importPDKModule("process")
if TYPE_CHECKING:
    pass


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

    def arrayViaNameChanged(self, text: str):
        via = [item for item in process.processVias if item.name == text][0]
        self.arrayViaWidthEdit.setText(str(via.minWidth))
        self.arrayViaHeightEdit.setText(str(via.minWidth))

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

        # Connect signal for polygon highlighting
        # self.drcTable.polygonSelected.connect(self.highlightPolygons)

    # def highlightPolygons(self, polygons):
    #     # Emit signal or call parentW method to highlight polygons in scene
    #     if hasattr(self.parentW(), 'highlightDRCPolygons'):
    #         self.parentW().highlightDRCPolygons(polygons)


class lvsResultsDialogue(QDialog):
    def __init__(self, parent, nets: list, devices: list):
        super().__init__(parent)
        self.layoutEditor = parent
        self._lvs_transform: tuple[float, float, int] | None = None
        self._highlight_colors = [
            QColor("#e11d48"),
            QColor("#0ea5e9"),
            QColor("#10b981"),
            QColor("#f59e0b"),
            QColor("#8b5cf6"),
            QColor("#ef4444"),
        ]
        self._highlight_color_index = 0
        self._net_color_by_signature: dict[tuple, QColor] = {}
        self.setWindowTitle("Revolution EDA LVS Results")
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        layout = QVBoxLayout()

        # Create tab widget
        self.tabWidget = QTabWidget()

        # Nets tab
        self.netsTab = QWidget()
        netsLayout = QVBoxLayout()
        self.lvsTable = lvsmv.LVSNetsTableView(nets)
        self.lvsTable.netSelected.connect(self.onNetSelected)
        netsLayout.addWidget(self.lvsTable)
        self.netsTab.setLayout(netsLayout)
        self.tabWidget.addTab(self.netsTab, "Nets")

        # devices tab (placeholder for future implementation)
        self.devicesTab = QWidget()
        devicesLayout = QVBoxLayout()
        devicesLabel = QLabel("Devices table will be implemented here.")
        devicesLayout.addWidget(devicesLabel)
        self.devicesTab.setLayout(devicesLayout)
        self.tabWidget.addTab(self.devicesTab, "Devices")

        # Mismatches tab (placeholder for future implementation)
        self.mismatchesTab = QWidget()
        mismatchesLayout = QVBoxLayout()
        mismatchesLabel = QLabel("Mismatches table will be implemented here.")
        mismatchesLayout.addWidget(mismatchesLabel)
        self.mismatchesTab.setLayout(mismatchesLayout)
        self.tabWidget.addTab(self.mismatchesTab, "Mismatches")

        layout.addWidget(self.tabWidget)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    @staticmethod
    def _shape_to_bbox(shape: dict) -> tuple[float, float, float, float] | None:
        if shape.get("type") == "rect":
            box = shape.get("bbox")
            if isinstance(box, list) and len(box) == 2:
                try:
                    x1 = float(box[0][0])
                    y1 = float(box[0][1])
                    x2 = float(box[1][0])
                    y2 = float(box[1][1])
                    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
                except (TypeError, ValueError, IndexError):
                    return None
        elif shape.get("type") == "polygon":
            points = shape.get("points", [])
            xs = [pt[0] for pt in points if isinstance(pt, (list, tuple)) and len(pt) >= 2]
            ys = [pt[1] for pt in points if isinstance(pt, (list, tuple)) and len(pt) >= 2]
            if xs and ys:
                return float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))
        return None

    def _infer_lvs_transform(self, shapes: list[dict]) -> tuple[float, float, int]:
        if self._lvs_transform is not None:
            return self._lvs_transform

        scene = self.layoutEditor.centralW.scene
        lvs_rects = []
        for shape in shapes:
            bbox = self._shape_to_bbox(shape)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            w = int(round(x2 - x1))
            h = int(round(y2 - y1))
            if w <= 0 or h <= 0:
                continue
            lvs_rects.append((int(round(x1)), int(round(y1)), w, h))

        if not lvs_rects:
            self._lvs_transform = (0.0, 0.0, 1)
            return self._lvs_transform

        scene_by_size: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        scene_rect_set: set[tuple[int, int, int, int]] = set()
        from revedaEditor.fileio.importlvsdb import LVSErrorRect

        for item in scene.items():
            if isinstance(item, LVSErrorRect):
                continue
            if not item.isVisible() or item.zValue() >= 100:
                continue
            rect = item.sceneBoundingRect().normalized()
            w = int(round(rect.width()))
            h = int(round(rect.height()))
            if w <= 0 or h <= 0:
                continue
            x = int(round(rect.left()))
            y = int(round(rect.top()))
            key = (w, h)
            if len(scene_by_size[key]) < 80:
                scene_by_size[key].append((x, y))
            scene_rect_set.add((x, y, w, h))

        if not scene_rect_set:
            self._lvs_transform = (0.0, 0.0, 1)
            return self._lvs_transform

        votes: Counter[tuple[int, int, int]] = Counter()
        for x, y, w, h in lvs_rects[:700]:
            candidates = scene_by_size.get((w, h), [])
            if not candidates:
                continue
            for sign in (1, -1):
                for X, Y in candidates:
                    votes[(sign, X - x, Y - sign * y)] += 1

        if not votes:
            self._lvs_transform = (0.0, 0.0, 1)
            return self._lvs_transform

        best = None
        best_matches = -1
        for (sign, dx, dy), _score in votes.most_common(20):
            matches = 0
            for x, y, w, h in lvs_rects:
                if (x + dx, sign * y + dy, w, h) in scene_rect_set:
                    matches += 1
            if matches > best_matches:
                best_matches = matches
                best = (float(dx), float(dy), int(sign))

        self._lvs_transform = best if best is not None else (0.0, 0.0, 1)
        return self._lvs_transform

    def _next_highlight_color(self) -> QColor:
        color = self._highlight_colors[
            self._highlight_color_index % len(self._highlight_colors)
        ]
        self._highlight_color_index += 1
        return color

    def _color_for_shapes(self, shapes: list[dict]) -> QColor:
        # Build a lightweight, stable signature from first few shape bounding boxes.
        signature_parts = []
        for shape in shapes[:8]:
            bbox = self._shape_to_bbox(shape)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            signature_parts.append(
                (
                    shape.get("type", ""),
                    int(round(x1)),
                    int(round(y1)),
                    int(round(x2 - x1)),
                    int(round(y2 - y1)),
                )
            )
        signature = tuple(signature_parts)
        if signature not in self._net_color_by_signature:
            self._net_color_by_signature[signature] = self._next_highlight_color()
        return self._net_color_by_signature[signature]

    def onNetSelected(self, shapes):
        from revedaEditor.fileio.importlvsdb import LVSErrorRect

        dx, dy, y_sign = self._infer_lvs_transform(shapes)
        color = self._color_for_shapes(shapes)
        lvsShapes = []
        for shape in shapes:
            bbox = self._shape_to_bbox(shape)
            if bbox is None:
                continue
            x1, y1, x2, y2 = bbox
            tx1 = x1 + dx
            tx2 = x2 + dx
            ty1 = y_sign * y1 + dy
            ty2 = y_sign * y2 + dy
            left = int(round(min(tx1, tx2)))
            top = int(round(min(ty1, ty2)))
            width = max(1, int(round(abs(tx2 - tx1))))
            height = max(1, int(round(abs(ty2 - ty1))))
            rect_item = LVSErrorRect(QRect(left, top, width, height))
            fill = QColor(color)
            fill.setAlpha(150)
            rect_item.setBrush(QBrush(fill))
            rect_item.setPen(QPen(color, 4, Qt.PenStyle.SolidLine))
            rect_item.setOpacity(0.9)
            lvsShapes.append(rect_item)

        self.layoutEditor.handleLVSRectSelection(lvsShapes)
