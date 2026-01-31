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

# properties dialogues for various editor functions

import pathlib

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtGui import (
    QFontDatabase,
)
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QButtonGroup,
    QTabWidget,
    QLineEdit,
    QLabel,
    QComboBox,
    QGroupBox,
    QRadioButton,
    QGridLayout,
    QTextEdit,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
)

import revedaEditor.common.labels as lbl
import revedaEditor.common.net as net
import revedaEditor.common.shapes as shp
import revedaEditor.gui.editFunctions as edf


class rectPropertyDialog(QDialog):
    """
    Property dialog for symbol rectangles.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumWidth(300)
        self.setWindowTitle("Rectangle Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 20, 10, 20)
        self.rectWidthLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Width:"), self.rectWidthLine)
        self.rectHeightLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Height:"), self.rectHeightLine)
        self.rectLeftLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("X Origin:"), self.rectLeftLine)
        self.rectTopLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Y Origin:"), self.rectTopLine)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class circlePropertyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setMinimumWidth(300)
        self.setWindowTitle("Circle Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 10, 10, 10)
        self.centerXEdit = edf.shortLineEdit()

        self.fLayout.addRow(QLabel("center x-coord:"), self.centerXEdit)
        self.centerYEdit = edf.shortLineEdit()

        self.fLayout.addRow(QLabel("center y-coord:"), self.centerYEdit)
        self.radiusEdit = edf.shortLineEdit()

        self.fLayout.addRow(QLabel("radius:"), self.radiusEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class arcPropertyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Arc Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 10, 10, 10)
        # self.mainLayout.addWidget(self.arcTypeCombo)
        self.startXEdit = edf.shortLineEdit()
        self.fLayout.addRow(edf.boldLabel("X Origin:"), self.startXEdit)
        self.startYEdit = edf.shortLineEdit()
        self.fLayout.addRow(edf.boldLabel("Y Origin:"), self.startYEdit)
        self.widthEdit = edf.shortLineEdit()

        self.fLayout.addRow(edf.boldLabel("Width:"), self.widthEdit)
        self.heightEdit = edf.shortLineEdit()
        self.fLayout.addRow(edf.boldLabel("Height:"), self.heightEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class linePropertyDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Line Properties")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.fLayout.setContentsMargins(10, 10, 10, 10)
        self.startXLine = QLineEdit()

        self.fLayout.addRow(QLabel("Start (X):"), self.startXLine)
        self.startYLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("Start (Y):"), self.startYLine)
        self.endXLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("End (X):"), self.endXLine)
        self.endYLine = edf.shortLineEdit()
        self.fLayout.addRow(QLabel("End (Y):"), self.endYLine)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class pointsTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Del.", 'X', "Y"])
        self.setColumnWidth(0, 8)
        self.setShowGrid(True)
        self.setGridStyle(Qt.SolidLine)


class symbolPolygonProperties(QDialog):
    def __init__(self, parent: QWidget, tupleList: list):
        super().__init__(parent)
        self.tupleList = tupleList
        self.setWindowTitle("Symbol Polygon Properties")
        self.setMinimumWidth(300)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
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
        delete_checkbox.stateChanged.connect(
            lambda state, r=row: self.deleteRow(r, state)
        )

    def addEmptyRow(self, row):

        # self.table_widget.insertRow(row)
        delete_checkbox = QCheckBox()
        self.tableWidget.setCellWidget(row, 0, delete_checkbox)
        delete_checkbox.stateChanged.connect(
            lambda state, r=row: self.deleteRow(r, state))

        self.tableWidget.setItem(row, 1, QTableWidgetItem(""))
        self.tableWidget.setItem(row, 2, QTableWidgetItem(""))

    def handleCellChange(self, row, column):
        if (
                row == self.tableWidget.rowCount() - 1
        ):  # Check if last row and tuple text column
            if self.tableWidget.item(row, 2) is not None:
                text1 = self.tableWidget.item(row, 1).text()
                text2 = self.tableWidget.item(row, 2).text()
                if text1 != "" and text2 != "":
                    self.tableWidget.insertRow(row + 1)
                    self.addEmptyRow(row + 1)

    def deleteRow(self, row, state):
        if state == 2:  # Checked state
            self.tableWidget.removeRow(row)


class createPinDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Pin")
        self.setMinimumWidth(300)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.pinName = edf.shortLineEdit()
        self.pinName.setPlaceholderText("Pin Name")
        self.pinName.setToolTip("Enter pin name")
        self.fLayout.addRow(QLabel("Pin Name"), self.pinName)
        self.pinDir = QComboBox()
        self.pinDir.addItems(shp.symbolPin.pinDirs)
        self.pinDir.setToolTip("Select pin direction")
        self.fLayout.addRow(QLabel("Pin Direction"), self.pinDir)
        self.pinType = QComboBox()
        self.pinType.addItems(shp.symbolPin.pinTypes)
        self.pinType.setToolTip("Select pin type")
        self.fLayout.addRow(QLabel("Pin Type"), self.pinType)
        self.mainLayout.addLayout(self.fLayout)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class pinPropertyDialog(createPinDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Pin Properties")
        self.pinXLine = edf.shortLineEdit()
        self.pinXLine.setToolTip("X Coordinate")
        self.fLayout.addRow(QLabel("X:"), self.pinXLine)
        self.pinYLine = edf.shortLineEdit()
        self.pinYLine.setToolTip("Y Coordinate")
        self.fLayout.addRow(QLabel("Y:"), self.pinYLine)


class createSymbolLabelDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Label")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.mainLayout = QVBoxLayout()
        self.fLayout = QFormLayout()
        self.labelDefinition = QLineEdit()
        self.labelDefinition.setPlaceholderText("Label Definition")
        self.labelDefinition.setToolTip("Enter label Definition")
        self.fLayout.addRow(QLabel("Label Definition"), self.labelDefinition)
        self.labelHeightEdit = QLineEdit()
        self.labelHeightEdit.setPlaceholderText("Label Height")
        self.labelHeightEdit.setToolTip("Enter label Height")
        self.fLayout.addRow(QLabel("Label Height"), self.labelHeightEdit)
        self.labelAlignCombo = QComboBox()
        self.labelAlignCombo.addItems(lbl.symbolLabel.labelAlignments)
        self.fLayout.addRow(QLabel("Label Alignment"), self.labelAlignCombo)
        self.labelOrientCombo = QComboBox()
        self.labelOrientCombo.addItems(lbl.symbolLabel.labelOrients)
        self.fLayout.addRow(QLabel("Label Orientation"), self.labelOrientCombo)
        self.labelUseCombo = QComboBox()
        self.labelUseCombo.addItems(lbl.symbolLabel.labelUses)
        self.fLayout.addRow(QLabel("Label Use"), self.labelUseCombo)
        self.labelVisiCombo = QComboBox()
        self.labelVisiCombo.addItems(["Yes", "No"])
        self.fLayout.addRow(QLabel("Label Visible"), self.labelVisiCombo)
        self.mainLayout.addLayout(self.fLayout)
        self.labelTypeGroup = QGroupBox("Label Type")
        self.labelTypeLayout = QHBoxLayout()
        self.normalType = QRadioButton(lbl.symbolLabel.labelTypes[0])
        self.normalType.setChecked(True)
        self.NLPType = QRadioButton(lbl.symbolLabel.labelTypes[1])
        self.pyLType = QRadioButton(lbl.symbolLabel.labelTypes[2])
        self.labelTypeLayout.addWidget(self.normalType)
        self.labelTypeLayout.addWidget(self.NLPType)
        self.labelTypeLayout.addWidget(self.pyLType)
        self.labelTypeGroup.setLayout(self.labelTypeLayout)
        self.mainLayout.addWidget(self.labelTypeGroup)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class labelPropertyDialog(createSymbolLabelDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Label Properties")
        self.labelXLine = edf.shortLineEdit()
        self.labelXLine.setToolTip("X Coordinate")
        self.fLayout.addRow(QLabel("X:"), self.labelXLine)
        self.labelYLine = edf.shortLineEdit()
        self.labelYLine.setToolTip("Y Coordinate")
        self.fLayout.addRow(QLabel("Y:"), self.labelYLine)


class symbolLabelsDialogue(QDialog):
    """
    Dialog for changing symbol labels and attributes. Symbol properties... menu item.
    """

    def __init__(self, parent, items: list, attributes: list):
        super().__init__(parent)
        self.parent = parent
        self.items = items
        self.attributes = attributes
        self.setWindowTitle("Symbol Labels")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.mainLayout = QVBoxLayout()
        self.symbolPropsLayout = QGridLayout()
        self.symbolLabelsLayout = QGridLayout()
        self.symbolAttrsMethod()
        # Symbol Labels Layout
        self.symbolLabelsMethod()
        labelsGroup = QGroupBox("Symbol Labels")
        labelsGroup.setLayout(self.symbolLabelsLayout)
        self.mainLayout.addWidget(labelsGroup)
        self.mainLayout.addStretch(1)
        # self.mainLayout.addLayout(self.symbolLabelsLayout)
        propsGroup = QGroupBox("Symbol Attributes")
        propsGroup.setLayout(self.symbolPropsLayout)
        self.mainLayout.addWidget(propsGroup)
        self.mainLayout.addStretch(1)
        # self.mainLayout.addLayout(self.symbolPropsLayout)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def symbolAttrsMethod(self):
        self.attributeNameList = []
        # self.attributeTypeList = []
        self.attributeDefList = []
        # Symbol Properties
        self.symbolPropsLayout.addWidget(QLabel("Attribute Name"), 0, 0)
        # self.symbolPropsLayout.addWidget(QLabel("Type"), 0, 1)
        self.symbolPropsLayout.addWidget(QLabel("Definition"), 0, 1)
        i = 0
        for item in self.attributes:
            self.attributeNameList.append(edf.longLineEdit())
            self.attributeNameList[i].setText(item.name)
            self.symbolPropsLayout.addWidget(self.attributeNameList[i], i + 1, 0)
            self.attributeDefList.append(edf.longLineEdit())
            self.attributeDefList[i].setText(item.definition)
            self.symbolPropsLayout.addWidget(self.attributeDefList[i], i + 1, 1)
            i += 1

        self.attributeNameList.append(edf.longLineEdit())
        self.attributeDefList.append(edf.longLineEdit())
        self.symbolPropsLayout.addWidget(self.attributeNameList[-1], i + 2, 0)
        self.symbolPropsLayout.addWidget(self.attributeDefList[-1], i + 2, 1)
        self.attributeNameList[-1].setPlaceholderText("Enter Attribute Name")
        self.attributeDefList[-1].setToolTip("Enter Attribute Definition")
        self.attributeDefList[-1].editingFinished.connect(
            lambda: self.updateAttributeDef(i + 1)
        )

    def updateAttributeDef(self, i):
        i += 1
        self.attributeNameList.append(edf.longLineEdit())
        self.attributeDefList.append(edf.longLineEdit())
        self.symbolPropsLayout.addWidget(self.attributeNameList[-1], i + 1, 0)
        self.symbolPropsLayout.addWidget(self.attributeDefList[-1], i + 1, 1)
        self.attributeNameList[-1].setPlaceholderText("Enter Attribute Name")
        self.attributeDefList[-1].setToolTip("Enter Attribute Definition")
        self.attributeDefList[-1].editingFinished.connect(
            lambda: self.updateAttributeDef(i)
        )

    def symbolLabelsMethod(self):
        self.labelDefinitionList = []
        self.labelHeightList = []
        self.labelAlignmentList = []
        self.labelOrientationList = []
        self.labelUseList = []
        self.labelTypeList = []
        self.labelItemList = []
        i = 0
        self.symbolLabelsLayout.addWidget(edf.boldLabel("Definition"), 0, 0)
        self.symbolLabelsLayout.addWidget(edf.boldLabel("Height"), 0, 1)
        self.symbolLabelsLayout.addWidget(edf.boldLabel("Alignment"), 0, 2)
        self.symbolLabelsLayout.addWidget(edf.boldLabel("Orientation"), 0, 3)
        self.symbolLabelsLayout.addWidget(edf.boldLabel("Use"), 0, 4)
        self.symbolLabelsLayout.addWidget(edf.boldLabel("Type"), 0, 5)
        for item in self.items:
            if type(item) == lbl.symbolLabel:
                i += 1
                self.labelItemList.append(item)
                self.labelDefinitionList.append(edf.longLineEdit())
                self.labelDefinitionList[-1].setText(item.labelDefinition)
                self.labelDefinitionList[-1].setReadOnly(True)
                self.symbolLabelsLayout.addWidget(self.labelDefinitionList[i - 1], i, 0)
                self.labelHeightList.append(edf.shortLineEdit())
                self.labelHeightList[-1].setText(str(item.labelHeight))
                self.symbolLabelsLayout.addWidget(self.labelHeightList[i - 1], i, 1)
                self.labelAlignmentList.append(QComboBox())
                self.labelAlignmentList[-1].addItems(lbl.symbolLabel.labelAlignments)
                self.labelAlignmentList[-1].setCurrentText(item.labelAlign)
                self.symbolLabelsLayout.addWidget(self.labelAlignmentList[-1], i, 2)
                self.labelOrientationList.append(QComboBox())
                self.labelOrientationList[-1].addItems(lbl.symbolLabel.labelOrients)
                self.labelOrientationList[-1].setCurrentText(item.labelOrient)
                self.symbolLabelsLayout.addWidget(self.labelOrientationList[-1], i, 3)
                self.labelUseList.append(QComboBox())
                self.labelUseList[-1].addItems(lbl.symbolLabel.labelUses)
                self.labelUseList[-1].setCurrentText(item.labelUse)
                self.symbolLabelsLayout.addWidget(self.labelUseList[-1], i, 4)
                self.labelTypeList.append(QComboBox())
                self.labelTypeList[-1].addItems(lbl.symbolLabel.labelTypes)
                self.labelTypeList[-1].setCurrentText(item.labelType)
                self.symbolLabelsLayout.addWidget(self.labelTypeList[-1], i, 5)
        if i == 0:  # no labels to edit
            self.symbolLabelsLayout.addWidget(QLabel("No symbol labels found."), 1, 0)


class instanceProperties(QDialog):
    def __init__(self, parent):
        # assert isinstance(instance, shp.symbolShape)
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Instance Properties")
        tabWidget = QTabWidget()
        mainLayout = QVBoxLayout()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        formLayout = QFormLayout()
        self.libNameEdit = edf.longLineEdit()
        self.libNameEdit.setReadOnly(True)
        self.libNameEdit.setToolTip("Library Name (Read Only)")
        formLayout.addRow(edf.boldLabel("Library Name", self), self.libNameEdit)
        self.cellNameEdit = edf.longLineEdit()
        self.cellNameEdit.setReadOnly(True)
        self.cellNameEdit.setToolTip("Cell Name (Read Only)")
        formLayout.addRow(edf.boldLabel("Cell Name", self), self.cellNameEdit)
        self.viewNameEdit = edf.longLineEdit()
        self.viewNameEdit.setReadOnly(True)
        self.viewNameEdit.setToolTip("View Name (Read Only)")
        formLayout.addRow(edf.boldLabel("View Name", self), self.viewNameEdit)
        self.instNameEdit = edf.longLineEdit()
        self.instNameEdit.setToolTip("Instance Name")
        formLayout.addRow(edf.boldLabel("Instance Name", self), self.instNameEdit)
        self.xLocationEdit = edf.shortLineEdit()
        formLayout.addRow(edf.boldLabel("x location", self), self.xLocationEdit)
        self.yLocationEdit = edf.shortLineEdit()
        formLayout.addRow(edf.boldLabel("y location", self), self.yLocationEdit)
        self.angleEdit = edf.longLineEdit()

        formLayout.addRow(edf.boldLabel("Angle", self), self.angleEdit)
        formLayout.setVerticalSpacing(10)
        mainLayout.addLayout(formLayout)
        propertiesGroup = QGroupBox()
        self.instanceLabelsLayout = QGridLayout()
        self.instanceLabelsLayout.setColumnMinimumWidth(0, 100)
        self.instanceLabelsLayout.setColumnMinimumWidth(1, 200)
        self.instanceLabelsLayout.setColumnMinimumWidth(2, 100)
        self.instanceLabelsLayout.setColumnStretch(0, 0)
        self.instanceLabelsLayout.setColumnStretch(1, 1)
        self.instanceLabelsLayout.setColumnStretch(2, 0)
        propertiesGroup.setLayout(self.instanceLabelsLayout)
        tabWidget.addTab(propertiesGroup, "Instance Properties")
        attributesGroup = QGroupBox()
        self.instanceAttributesLayout = QGridLayout()
        self.instanceAttributesLayout.setColumnMinimumWidth(0, 100)
        self.instanceAttributesLayout.setColumnMinimumWidth(1, 200)
        self.instanceAttributesLayout.setColumnStretch(0, 0)
        self.instanceAttributesLayout.setColumnStretch(1, 1)
        attributesGroup.setLayout(self.instanceAttributesLayout)
        tabWidget.addTab(attributesGroup, "Instance Attributes")
        mainLayout.addWidget(tabWidget)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


class netNameDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Add Net Name")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        buttonBox = QDialogButtonBox(QBtn)
        mainLayout = QVBoxLayout()
        formLayout = QFormLayout()
        self.netNameEdit = edf.longLineEdit()
        self.netNameEdit.setToolTip("Enter net name")
        formLayout.addRow(edf.boldLabel("Net Name", self), self.netNameEdit)
        mainLayout.addLayout(formLayout)
        mainLayout.addSpacing(40)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)


class netProperties(QDialog):
    def __init__(self, parent):
        # assert isinstance(instance, shp.symbolShape)
        super().__init__(parent)
        self.parent = parent
        self.net = net
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Net Properties")
        mainLayout = QVBoxLayout()
        okButton = QDialogButtonBox.Ok
        cancelButton = QDialogButtonBox.Cancel
        QBtn = okButton | cancelButton
        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.button(QDialogButtonBox.Ok).setDefault(True)
        netPointsBox = QGroupBox("Net Points")
        netPointsLayout = QFormLayout()
        netPointsBox.setLayout(netPointsLayout)
        self.netStartPointEditX = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("Net Start X:"), self.netStartPointEditX)
        self.netStartPointEditY = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("Net Start Y:"), self.netStartPointEditY)
        self.netEndPointEditX = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("End Point X:"), self.netEndPointEditX)
        self.netEndPointEditY = edf.shortLineEdit()
        netPointsLayout.addRow(edf.boldLabel("End Point X:"), self.netEndPointEditY)

        netWidthGroupBox = QGroupBox('Net Width')
        netWidthLayout = QHBoxLayout()
        narrowNetButton = QRadioButton('Narrow')
        wideNetButton = QRadioButton('Wide')
        netWidthLayout.addWidget(narrowNetButton)
        netWidthLayout.addWidget(wideNetButton)
        self.widthButtonGroup = QButtonGroup(self)
        self.widthButtonGroup.addButton(narrowNetButton)
        self.widthButtonGroup.addButton(wideNetButton)
        self.widthButtonGroup.setId(narrowNetButton, 0)
        self.widthButtonGroup.setId(wideNetButton, 1)
        netWidthGroupBox.setLayout(netWidthLayout)
        mainLayout.addWidget(netWidthGroupBox)
        formBox = QGroupBox("Net Properties")
        formLayout = QFormLayout()
        self.netNameEdit = edf.longLineEdit()
        formLayout.addRow(edf.boldLabel("Net Name", self), self.netNameEdit)
        formBox.setLayout(formLayout)
        mainLayout.addWidget(formBox)
        mainLayout.addSpacing(20)
        mainLayout.addWidget(netPointsBox)
        mainLayout.addSpacing(40)
        mainLayout.addWidget(buttonBox)
        self.setLayout(mainLayout)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.show()


class createSchematicPinDialog(createPinDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Create Schematic Pin")


class schematicPinPropertiesDialog(createPinDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Pin Properties")
        self.xlocationEdit = edf.shortLineEdit()
        self.xlocationEdit.setToolTip("x location of pin")
        self.fLayout.addRow("x location:", self.xlocationEdit)
        self.ylocationEdit = edf.shortLineEdit()
        self.ylocationEdit.setToolTip("y location of pin")
        self.fLayout.addRow("y location:", self.ylocationEdit)
        self.angleEdit = edf.shortLineEdit()
        self.angleEdit.setToolTip("angle of pin")
        self.fLayout.addRow("angle:", self.angleEdit)


class symbolNameDialog(QDialog):
    def __init__(self, cellPath: pathlib.Path, cellName: str, parent):
        super().__init__(parent)
        self.cellPath = cellPath
        self.cellName = cellName
        self.symbolViewNames = [
            view.stem for view in cellPath.iterdir() if "symbol" in view.stem
        ]
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Create a symbol?")
        self.mainLayout = QVBoxLayout()
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        formLayout = QFormLayout()
        formLayout.addRow(
            edf.boldLabel("Library Name"), QLabel(self.cellPath.parent.stem)
        )
        formLayout.addRow(edf.boldLabel("Cell Name"), QLabel(self.cellPath.stem))
        self.symbolViewsCB = QComboBox()
        self.symbolViewsCB.addItems(self.symbolViewNames)
        self.symbolViewsCB.setEditable(True)
        formLayout.addRow(edf.boldLabel("Symbol View Name:"), self.symbolViewsCB)
        self.mainLayout.addLayout(formLayout)
        self.mainLayout.addSpacing(40)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


class symbolCreateDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Create Symbol")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.mainLayout = QVBoxLayout()

        self.fLayout = QFormLayout()
        self.topPinsEdit = edf.longLineEdit()
        self.topPinsEdit.setToolTip("Enter top pins")
        self.fLayout.addRow(edf.boldLabel("Top Pins:"), self.topPinsEdit)
        self.leftPinsEdit = edf.longLineEdit()
        self.leftPinsEdit.setToolTip("Enter left pins")
        self.fLayout.addRow(edf.boldLabel("Left Pins:"), self.leftPinsEdit)
        self.bottomPinsEdit = edf.longLineEdit()
        self.bottomPinsEdit.setToolTip("Enter bottom pins")
        self.fLayout.addRow(edf.boldLabel("Bottom Pins:"), self.bottomPinsEdit)
        self.rightPinsEdit = edf.longLineEdit()
        self.rightPinsEdit.setToolTip("Enter right pins")
        self.fLayout.addRow(edf.boldLabel("Right Pins:"), self.rightPinsEdit)
        self.mainLayout.addLayout(self.fLayout)
        self.mainLayout.addSpacing(20)
        self.geomLayout = QFormLayout()
        self.stubLengthEdit = QLineEdit()
        self.stubLengthEdit.setText("60")
        self.stubLengthEdit.setToolTip("Enter stub lengths")
        self.geomLayout.addRow(edf.boldLabel("Stub Length:"), self.stubLengthEdit)
        self.pinDistanceEdit = QLineEdit()
        self.pinDistanceEdit.setText("80")
        self.pinDistanceEdit.setToolTip("Enter pin spacing")
        self.geomLayout.addRow(edf.boldLabel("Pin spacing:"), self.pinDistanceEdit)
        self.mainLayout.addLayout(self.geomLayout)
        self.mainLayout.addSpacing(40)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        self.show()


class noteTextEdit(QDialog):
    """
    Set text properties.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Edit Text")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        mainLayout = QVBoxLayout()
        self.plainTextEdit = QTextEdit()
        mainLayout.addWidget(self.plainTextEdit)
        fontFamilies = QFontDatabase.families(QFontDatabase.Latin)
        fixedFamilies = [
            family for family in fontFamilies if QFontDatabase.isFixedPitch(family)
        ]
        formLayout = QFormLayout()
        self.familyCB = QComboBox()
        self.familyCB.addItems(fixedFamilies)
        self.familyCB.currentTextChanged.connect(self.familyFontStyles)
        formLayout.addRow(edf.boldLabel("Font Name"), self.familyCB)
        self.fontStyleCB = QComboBox()
        self.fontStyles = QFontDatabase.styles(fixedFamilies[0])
        self.fontStyleCB.addItems(self.fontStyles)
        self.fontStyleCB.currentTextChanged.connect(self.styleFontSizes)
        formLayout.addRow(edf.boldLabel("Font Style"), self.fontStyleCB)
        self.fontsizeCB = QComboBox()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(fixedFamilies[0], self.fontStyles[0])
        ]
        self.fontsizeCB.addItems(self.fontSizes)
        formLayout.addRow(edf.boldLabel("Font Size"), self.fontsizeCB)
        self.textAlignmCB = QComboBox()
        self.textAlignmCB.addItems(shp.text.textAlignments)
        formLayout.addRow(edf.boldLabel("Text Alignment"), self.textAlignmCB)
        self.textOrientCB = QComboBox()
        self.textOrientCB.addItems(shp.text.textOrients)
        formLayout.addRow(edf.boldLabel("Text Orientation"), self.textOrientCB)
        mainLayout.addLayout(formLayout)
        mainLayout.addSpacing(40)
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)
        self.show()

    def familyFontStyles(self, s):
        self.fontStyleCB.clear()
        self.fontStyles = QFontDatabase.styles(self.familyCB.currentText())
        self.fontStyleCB.addItems(self.fontStyles)

    def styleFontSizes(self, s):
        self.fontsizeCB.clear()
        selectedFamily = self.familyCB.currentText()
        selectedStyle = self.fontStyleCB.currentText()
        self.fontSizes = [
            str(size)
            for size in QFontDatabase.pointSizes(selectedFamily, selectedStyle)
        ]
        self.fontsizeCB.addItems(self.fontSizes)


class displayConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Display Options")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.vLayout = QVBoxLayout()
        gridValueGroup = QGroupBox("Grid Values")
        self.fLayout = QFormLayout()
        gridValueGroup.setLayout(self.fLayout)
        self.majorGridEntry = QLineEdit()
        self.majorGridEntry.setToolTip(
            "Enter Dot or Line Grid Spacing Value as a multiple of scene grid"
        )
        self.fLayout.addRow("GridSpacing:", self.majorGridEntry)
        self.snapGridEdit = QLineEdit()
        self.snapGridEdit.setToolTip(
            "Enter the Snap Grid Value as a multiple of scene grid"
        )
        self.fLayout.addRow("Snap Distance", self.snapGridEdit)

        gridTypeGroup = QGroupBox("Grid Type")
        gridTypeLayout = QHBoxLayout()
        self.dotType = QRadioButton("Dot Grid")
        self.dotType.setChecked(True)
        self.lineType = QRadioButton("Line Grid")
        self.noType = QRadioButton("No Grid")
        gridTypeLayout.addWidget(self.dotType)
        gridTypeLayout.addWidget(self.lineType)
        gridTypeLayout.addWidget(self.noType)
        gridTypeGroup.setLayout(gridTypeLayout)

        self.vLayout.addWidget(gridValueGroup)
        self.vLayout.addWidget(gridTypeGroup)
        self.vLayout.addStretch(1)

        self.vLayout.addWidget(self.buttonBox)
        self.setLayout(self.vLayout)
        self.show()


class layoutDisplayConfigDialog(displayConfigDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Layout Display Options")
        self.dbuEntry = edf.shortLineEdit()
        self.dbuEntry.setToolTip("Number of points per um")
        self.dbuEntry.setReadOnly(True)
        self.fLayout.insertRow(0, "Process Points per um:", self.dbuEntry)


class selectConfigDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Selection Options")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        vLayout = QVBoxLayout()
        selectionTypeGroup = QGroupBox("Selection Type")
        selectionTypeLayout = QHBoxLayout()
        self.fullSelection = QRadioButton("Full")
        self.partialSelection = QRadioButton("Partial")
        selectionTypeLayout.addWidget(self.fullSelection)
        selectionTypeLayout.addWidget(self.partialSelection)
        selectionTypeGroup.setLayout(selectionTypeLayout)
        vLayout.addWidget(selectionTypeGroup)
        # snapDistanceGroup = QGroupBox("Snap Distance")
        # snapDistanceLayout = QFormLayout()
        # self.snapDistanceEntry = edf.shortLineEdit()
        # snapDistanceLayout.addRow("Snap Distance", self.snapDistanceEntry)
        # snapDistanceGroup.setLayout(snapDistanceLayout)
        # vLayout.addWidget(snapDistanceGroup)
        vLayout.addStretch(1)
        vLayout.addWidget(self.buttonBox)
        self.setLayout(vLayout)
        self.show()


class moveByDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.setWindowTitle("Move By...")
        self.setMinimumWidth(250)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout = QVBoxLayout()
        coordsGroup = QGroupBox("Move By")
        coordsLayout = QFormLayout()
        self.xEdit = edf.shortLineEdit()
        self.yEdit = edf.shortLineEdit()
        coordsLayout.addRow("Move By in X:", self.xEdit)
        coordsLayout.addRow("Move By in Y:", self.yEdit)
        coordsGroup.setLayout(coordsLayout)
        self.mainLayout.addWidget(coordsGroup)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
