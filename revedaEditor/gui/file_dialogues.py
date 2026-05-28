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
#    Commons Clause Lic\ense Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#


import datetime
import pathlib

from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QGroupBox,
    QTableView,
    QMenu,
    QCheckBox,
)

import revedaEditor.backend.library_methods as libm
import revedaEditor.gui.edit_functions as edf


class CreateCellDialog(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent=parent)
        self.parent = parent
        self.model = model
        self.init_UI()

    def init_UI(self):
        self.setWindowTitle("Create Cell")
        self.layout = QFormLayout()
        self.layout.setSpacing(10)
        self.libNamesCB = QComboBox()
        self.libNamesCB.setModel(self.model)
        self.libNamesCB.setModelColumn(0)
        self.libNamesCB.setCurrentIndex(0)
        self.libNamesCB.currentTextChanged.connect(self.selectLibrary)
        self.layout.addRow(edf.BoldLabel("Library:"), self.libNamesCB)
        self.cellCB = QComboBox()
        libItem = libm.getLibItem(self.model, self.libNamesCB.currentText())
        self.cellList = sorted(
            [libItem.child(i).cellName for i in range(libItem.rowCount())])
        self.cellCB.addItems(self.cellList)
        self.cellCB.setEditable(True)
        self.layout.addRow(edf.BoldLabel("Cell Name:"), self.cellCB)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def selectLibrary(self):
        libItem = libm.getLibItem(self.model, self.libNamesCB.currentText())
        cellList = sorted([libItem.child(i).cellName for i in range(libItem.rowCount())])
        self.cellCB.clear()
        self.cellCB.addItems(cellList)


class DeleteCellDialog(CreateCellDialog):
    def __init__(self, parent, model):
        super().__init__(parent, model)
        self.cellCB.setEditable(False)
        self.setWindowTitle("Delete Cell")


class NewCellViewDialog(CreateCellDialog):
    def __init__(self, parent, model):
        super().__init__(parent, model)
        self.cellCB.setEditable(False)
        self.setWindowTitle("Create Cell View")
        self.viewType = QComboBox()
        self.viewType.currentIndexChanged.connect(self.setCurrentViewName)
        self.layout.addRow(edf.BoldLabel("View Type:"), self.viewType)
        self.viewName = edf.LongLineEdit()
        self.layout.addRow(edf.BoldLabel("View Name:"), self.viewName)
        self.layout.setSpacing(10)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def setCurrentViewName(self):
        self.viewName.setText(self.viewType.currentText())


class SelectCellViewDialog(CreateCellDialog):
    def __init__(self, parent, model):
        super().__init__(parent=parent, model=model)
        libItem = libm.getLibItem(self.model, self.libNamesCB.currentText())
        self.setWindowTitle("Select CellView")
        self.cellCB.setEditable(False)
        self.cellCB.currentTextChanged.connect(self.cellNameChanged)
        self.viewCB = QComboBox()
        CellItem = libm.getCellItem(libItem, self.cellCB.currentText())
        # self.viewCB.addItems(
        #     [CellItem.child(i).text() for i in range(CellItem.rowCount())]
        # )
        self.viewCB.addItems(
            sorted([CellItem.child(i).text() for i in range(CellItem.rowCount())])
        )
        self.layout.addRow(edf.BoldLabel("View Name:"), self.viewCB)
        self.layout.setSpacing(10)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def cellNameChanged(self):
        libItem = libm.getLibItem(self.model, self.libNamesCB.currentText())
        CellItem = libm.getCellItem(libItem, self.cellCB.currentText())
        if CellItem is not None:
            viewList = [CellItem.child(i).text() for i in range(CellItem.rowCount())]
        else:
            viewList = []
        self.viewCB.clear()
        self.viewCB.addItems(viewList)


class RenameCellDialog(QDialog):
    def __init__(self, parent, CellItem):
        super().__init__(parent=parent)
        self.parent = parent
        self.CellItem = CellItem

        self.init_UI()

    def init_UI(self):
        self.setWindowTitle("Rename Cell")
        layout = QFormLayout()
        layout.setSpacing(10)
        self.nameEdit = QLineEdit()
        self.nameEdit.setPlaceholderText("Cell Name")
        self.nameEdit.setFixedWidth(200)
        layout.addRow(edf.BoldLabel("Cell Name:"), self.nameEdit)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addRow(self.buttonBox)
        self.setLayout(layout)


class CopyCellDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent

        # self.index = 0
        self.init_UI()

    def init_UI(self):
        self.setWindowTitle("Copy Cell")
        layout = QFormLayout()
        layout.setSpacing(10)
        self.libraryCB = QComboBox()
        self.selectedLibPath = self.libraryCB.itemData(0, Qt.ItemDataRole.UserRole + 2)
        self.libraryCB.currentTextChanged.connect(self.selectLibrary)
        layout.addRow(edf.BoldLabel("Library:"), self.libraryCB)
        self.copyName = QLineEdit()
        self.copyName.setPlaceholderText("Enter Cell Name")
        self.copyName.setFixedWidth(130)
        layout.addRow(edf.BoldLabel("Cell Name:"), self.copyName)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addRow(self.buttonBox)
        self.setLayout(layout)

    def selectLibrary(self):
        self.selectedLibPath = self.libraryCB.itemData(
            self.libraryCB.currentIndex(), Qt.ItemDataRole.UserRole + 2
        )


class CopyViewDialog(CreateCellDialog):
    def __init__(self, parent, model):
        super().__init__(parent=parent, model=model)
        self.setWindowTitle("Copy View")
        self.cellCB.setEditable(True)
        self.cellCB.InsertPolicy = QComboBox.InsertAfterCurrent
        self.viewName = edf.LongLineEdit()
        self.layout.addRow(edf.BoldLabel("View Name:"), self.viewName)
        self.layout.setSpacing(10)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class CloseLibDialog(QDialog):
    def __init__(self, libraryDict, parent, *args):
        super().__init__(parent, *args)
        self.libraryDict = libraryDict
        self.setWindowTitle("Select Library to close")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        formLayout = QFormLayout()
        self.libNamesCB = QComboBox()
        self.libNamesCB.addItems(self.libraryDict.keys())
        formLayout.addRow(edf.BoldLabel("Select Library", self), self.libNamesCB)
        layout.addLayout(formLayout)
        layout.addSpacing(40)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class RenameLibDialog(QDialog):
    def __init__(self, parent, oldLibraryName, *args):
        super().__init__(parent, *args)
        self.oldLibraryName = oldLibraryName
        self.setWindowTitle(f"Change {oldLibraryName} to:")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        formBox = QGroupBox("Rename Library")
        layout = QVBoxLayout()
        formLayout = QFormLayout()
        self.newLibraryName = edf.LongLineEdit()
        formLayout.addRow(edf.BoldLabel("New Library Name:", self), self.newLibraryName)
        formBox.setLayout(formLayout)
        layout.addWidget(formBox)
        layout.addSpacing(40)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class RenameViewDialog(QDialog):
    def __init__(self, parent, oldViewName):
        super().__init__(parent)
        self.oldViewName = oldViewName
        self.setWindowTitle(f"Rename {oldViewName} ")
        self.layout = QVBoxLayout()
        formLayout = QFormLayout()
        oldViewNameEdit = edf.LongLineEdit()
        oldViewNameEdit.setText(self.oldViewName)
        oldViewNameEdit.setEnabled(False)
        formLayout.addRow(edf.BoldLabel("Old View Name:"), oldViewNameEdit)
        self.newViewNameEdit = edf.LongLineEdit()
        formLayout.addRow(edf.BoldLabel("New View Name:"), self.newViewNameEdit)
        self.layout.addLayout(formLayout)
        self.layout.setSpacing(10)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class DeleteSymbolDialog(QDialog):
    def __init__(self, cellName, viewName, *args):
        super().__init__(*args)
        self.setWindowTitle(f"Delete {cellName}-{viewName} CellView?")
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        message = QLabel(f"{cellName}-{viewName} will be recreated!")
        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class NetlistExportDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle(f"Export Netlist for {parent.cellName}-{parent.viewName}")
        # self.setMinimumSize(500, 100)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addStretch(2)
        viewBox = QGroupBox("Select a view to Netlist")
        viewBoxLayout = QFormLayout()
        self.libNameEdit = edf.LongLineEdit()
        self.libNameEdit.setDisabled(True)
        viewBoxLayout.addRow(edf.BoldLabel("Library:"), self.libNameEdit)
        self.cellNameEdit = edf.LongLineEdit()
        self.cellNameEdit.setDisabled(True)
        viewBoxLayout.addRow(edf.BoldLabel("Cell:"), self.cellNameEdit)
        self.viewNameCombo = QComboBox()
        viewBoxLayout.addRow(edf.BoldLabel("View:"), self.viewNameCombo)
        viewBox.setLayout(viewBoxLayout)
        self.mainLayout.addWidget(viewBox)
        switchBox = QGroupBox("Switch and Stop View Lists")
        self.formLayout = QFormLayout()
        self.switchViewEdit = edf.LongLineEdit()
        self.switchViewEdit.setText((", ").join(self.parent.switchViewList))
        self.formLayout.addRow(edf.BoldLabel("Switch View List:"), self.switchViewEdit)
        self.stopViewEdit = edf.LongLineEdit()
        self.stopViewEdit.setText((", ").join(self.parent.stopViewList))
        self.formLayout.addRow((edf.BoldLabel("Stop View: ")), self.stopViewEdit)
        switchBox.setLayout(self.formLayout)
        self.mainLayout.addWidget(switchBox)
        netlistOptionBox = QGroupBox("Netlist Options")
        netlistOptLayout = QVBoxLayout()
        self.topAsSubcktCheckBox = QCheckBox("Netlist top level as subcircuit")
        self.topAsSubcktCheckBox.setChecked(False)
        netlistOptLayout.addWidget(self.topAsSubcktCheckBox)
        self.netlistFormatCombo = QComboBox()
        self.netlistFormatCombo.addItems(["Spice/Xyce", "Spectre/Vacask"])
        netlistOptLayout.addWidget(edf.BoldLabel("Netlist Format:"))
        netlistOptLayout.addWidget(self.netlistFormatCombo)
        netlistOptionBox.setLayout(netlistOptLayout)
        self.mainLayout.addWidget(netlistOptionBox)
        fileBox = QGroupBox("Select Simulation Directory")
        fileDialogLayout = QHBoxLayout()
        fileDialogLayout.addWidget(edf.BoldLabel("Export Directory:"))
        self.netlistDirEdit = edf.LongLineEdit()
        fileDialogLayout.addWidget(self.netlistDirEdit)
        self.netListDirButton = QPushButton("...")
        self.netListDirButton.clicked.connect(self.onDirButtonClicked)
        fileDialogLayout.addWidget(self.netListDirButton)
        fileBox.setLayout(fileDialogLayout)
        self.mainLayout.addWidget(fileBox)
        self.mainLayout.addStretch(2)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)

    def onDirButtonClicked(self):
        self.dirName = QFileDialog.getExistingDirectory()
        if self.dirName:
            self.netlistDirEdit.setText(self.dirName)


class LayoutExportDialogue(QDialog):
    def __init__(self, parentW, export_format="GDS"):
        super().__init__(parentW)
        self.parentW = parentW
        self.export_format = export_format.upper()
        self.setMinimumWidth(500)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addStretch(2)
        settingsBox = QGroupBox(f"{self.export_format} Export Settings")
        settingsBoxLayout = QFormLayout()
        settingsBox.setLayout(settingsBoxLayout)
        self.unitEdit = edf.ShortLineEdit()
        self.unitEdit.setToolTip(f"The unit of the {self.export_format} file.")
        settingsBoxLayout.addRow(edf.BoldLabel("Unit:"), self.unitEdit)
        self.precisionEdit = edf.ShortLineEdit()
        self.precisionEdit.setToolTip(f"The precision of the {self.export_format} file.")
        settingsBoxLayout.addRow(edf.BoldLabel("Precision:"), self.precisionEdit)
        self.mainLayout.addWidget(settingsBox)
        fileBox = QGroupBox(f"{self.export_format} Export Directory")
        fileDialogLayout = QHBoxLayout()
        fileDialogLayout.addWidget(edf.BoldLabel("Export Directory/File:"))
        self.exportPathEdit = edf.LongLineEdit()
        fileDialogLayout.addWidget(self.exportPathEdit)
        self.exportButton = QPushButton("...")
        self.exportButton.clicked.connect(self.onDirButtonClicked)
        fileDialogLayout.addWidget(self.exportButton)
        fileBox.setLayout(fileDialogLayout)
        self.mainLayout.addWidget(fileBox)
        self.mainLayout.addStretch(2)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)

    def onDirButtonClicked(self):
        dirName = QFileDialog.getExistingDirectory()
        if dirName:
            self.exportPathEdit.setText(
                f"{dirName}/{self.parentW.cellName}"
            )


class GdsExportDialogue(LayoutExportDialogue):
    def __init__(self, parentW):
        super().__init__(parentW, "GDS")


class OasExportDialogue(LayoutExportDialogue):
    def __init__(self, parentW):
        super().__init__(parentW, "OAS")

class GdsImportDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle(f"Import GDS File")
        self.setMinimumWidth(500)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addStretch(2)
        settingsBox = QGroupBox("GDS Import Settings")
        settingsBoxLayout = QFormLayout()
        settingsBox.setLayout(settingsBoxLayout)
        self.libNameEdit = edf.LongLineEdit()
        self.libNameEdit.setToolTip("The name of the library to import the GDS into.")
        settingsBoxLayout.addRow(edf.BoldLabel("Import Library Name:"), self.libNameEdit)
        self.unitEdit = edf.ShortLineEdit()
        self.unitEdit.setToolTip("The unit of the GDS file.")
        settingsBoxLayout.addRow(edf.BoldLabel("Unit:"), self.unitEdit)
        self.precisionEdit = edf.ShortLineEdit()
        self.precisionEdit.setToolTip("The precision of the GDS file.")
        settingsBoxLayout.addRow(edf.BoldLabel("Precision:"), self.precisionEdit)
        self.mainLayout.addWidget(settingsBox)
        fileBox = QGroupBox("GDS File")
        fileDialogLayout = QHBoxLayout()
        fileDialogLayout.addWidget(edf.BoldLabel("GDS File:"))
        self.inputFileEdit = edf.LongLineEdit()
        fileDialogLayout.addWidget(self.inputFileEdit)
        self.gdsImportButton = QPushButton("...")
        self.gdsImportButton.clicked.connect(self.onFileButtonClicked)
        fileDialogLayout.addWidget(self.gdsImportButton)
        fileBox.setLayout(fileDialogLayout)
        self.mainLayout.addWidget(fileBox)
        self.mainLayout.addStretch(2)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)

    def onFileButtonClicked(self):
        gdsFileName, _ = QFileDialog.getOpenFileName(self, caption="Select GDS file.",
                                                     filter="GDS files (*.gds)")
        if gdsFileName:
            self.inputFileEdit.setText(
                gdsFileName
            )


class GoDownHierDialogue(QDialog):
    def __init__(
            self,
            parent,
    ):
        super().__init__(parent=parent)
        self._parent = parent
        self.setWindowTitle("Go Down Hierarchy")
        self.setMinimumWidth(250)
        self.buttonId = 1
        _mainLayout = QVBoxLayout()
        viewGroup = QGroupBox("Select a cellview")
        viewGroupLayout = QVBoxLayout()
        viewGroup.setLayout(viewGroupLayout)
        self.viewListCB = QComboBox()
        viewGroupLayout.addWidget(self.viewListCB)
        _mainLayout.addWidget(viewGroup)
        buttonGroupBox = QGroupBox("Open")
        buttonGroupLayout = QHBoxLayout()
        buttonGroupBox.setLayout(buttonGroupLayout)
        self.openButton = QRadioButton("Edit")
        self.openButton.setChecked(True)
        self.readOnlyButton = QRadioButton("Read Only")
        buttonGroupLayout.addWidget(self.openButton)
        buttonGroupLayout.addWidget(self.readOnlyButton)
        _mainLayout.addWidget(buttonGroupBox)
        self.buttonGroup = QButtonGroup()
        self.buttonGroup.addButton(self.openButton, id=1)
        self.buttonGroup.addButton(self.readOnlyButton, id=2)
        self.buttonGroup.buttonClicked.connect(self.onButtonClicked)
        _mainLayout.addWidget(buttonGroupBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        _mainLayout.addWidget(buttonBox)
        self.setLayout(_mainLayout)

    def onButtonClicked(self):
        self.buttonId = self.buttonGroup.checkedId()


class ImportCellDialogue(QDialog):
    def __init__(self, model, parent, file_type="Verilog-A"):
        super().__init__(parent)
        self._parent = parent
        self.file_type = file_type
        self._model = model

        # Configure dialog based on file type
        if file_type == "Verilog-A":
            self.setWindowTitle("Import a Verilog-a Module File")
            self.setMinimumSize(500, 400)
            self.file_extension = ".va"
            self.file_filter = "Verilog-A files (*.va)"
            self.file_label = "Select Verilog-A file:"
            self.view_label = "Verilog-A view:"
            self.caption = "Select Verilog-A file."
        elif file_type == "Spice":
            self.setWindowTitle("Import a Spice Subcircuit File")
            self.setMinimumSize(500, 200)
            self.file_extension = ".sp"
            self.file_filter = "Spice files (*.sp, *.cir)"
            self.file_label = "Select Spice file:"
            self.view_label = "Spice  cellview:"
            self.caption = "Select Spice file."

        self._setup_ui()
        self.show()

    def _setup_ui(self):
        mainLayout = QVBoxLayout()
        fileDialogLayout = QHBoxLayout()
        fileDialogLayout.addWidget(edf.BoldLabel(self.file_label), 1)
        self.fileEdit = edf.LongLineEdit()
        fileDialogLayout.addWidget(self.fileEdit, 4)
        self.fileButton = QPushButton("...")
        self.fileButton.clicked.connect(self.onFileButtonClicked)
        fileDialogLayout.addWidget(self.fileButton, 1)
        mainLayout.addLayout(fileDialogLayout)
        mainLayout.addSpacing(20)

        layout = QFormLayout()
        layout.setSpacing(10)
        self.libNamesCB = QComboBox()
        self.libNamesCB.setModel(self._model)
        self.libNamesCB.currentTextChanged.connect(self.changeCells)
        layout.addRow(edf.BoldLabel("Library:"), self.libNamesCB)
        self.cellNamesCB = QComboBox()
        self.cellNamesCB.setEditable(True)

        # Handle initial cell names
        try:
            if self.file_type == "Verilog-A":
                try:
                    initialCellNames = [
                        self._model.item(0).child(i).cellName
                        for i in range(self._model.item(0).rowCount())
                    ]
                except Exception as e:
                    initialCellNames = []
                    print(f'No libraries could be found.')
            else:  # Spice
                initialCellNames = [
                    self._model.item(0).child(i).cellName
                    for i in range(self._model.item(0).rowCount())
                ]
        except (AttributeError, IndexError):
            initialCellNames = []

        self.cellNamesCB.addItems(initialCellNames)
        layout.addRow(edf.BoldLabel("Cell:"), self.cellNamesCB)
        self.viewName = edf.LongLineEdit()
        layout.addRow(edf.BoldLabel(self.view_label), self.viewName)
        mainLayout.addLayout(layout)

        symbolGroupBox = QGroupBox("Symbol Creation")
        symbolGBLayout = QVBoxLayout()
        self.symbolCheckBox = QCheckBox("Create a new symbol?")
        symbolGBLayout.addWidget(self.symbolCheckBox)
        symbolGroupBox.setLayout(symbolGBLayout)
        mainLayout.addWidget(symbolGroupBox)
        mainLayout.addSpacing(20)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)

    def changeCells(self):
        selectedLibItemRow = self._model.findItems(self.libNamesCB.currentText())[
            0
        ].row()
        libCellNames = [
            self._model.item(selectedLibItemRow).child(i).cellName
            for i in range(self._model.item(selectedLibItemRow).rowCount())
        ]
        self.cellNamesCB.clear()
        self.cellNamesCB.addItems(libCellNames)

    def onFileButtonClicked(self):
        filePathObj = pathlib.Path(self.fileEdit.text())
        fileDialog = QFileDialog()
        fileDialog.setNameFilter(self.file_filter)
        fileDialog.setDirectory(str(filePathObj.parent))
        fileDialog.selectFile(filePathObj.name)
        fileName = fileDialog.getOpenFileName(
            self, caption=self.caption
        )[0]
        if fileName:
            self.fileEdit.setText(fileName)


class ImportVerilogaCellDialogue(ImportCellDialogue):
    def __init__(self, model, parent):
        super().__init__(model, parent, "Verilog-A")

    @property
    def vaFileEdit(self):
        """Compatibility property for existing code"""
        return self.fileEdit

    @property
    def vaViewName(self):
        """Compatibility property for existing code"""
        return self.viewName

    @property
    def vaFileName(self):
        """Compatibility property for existing code"""
        return getattr(self, '_fileName', None)

    @vaFileName.setter
    def vaFileName(self, value):
        self._fileName = value


class ImportSpiceCellDialogue(ImportCellDialogue):
    def __init__(self, model, parent):
        super().__init__(model, parent, "Spice")

    @property
    def spiceFileEdit(self):
        """Compatibility property for existing code"""
        return self.fileEdit

    @property
    def spiceViewName(self):
        """Compatibility property for existing code"""
        return self.viewName

    @property
    def spiceFileName(self):
        """Compatibility property for existing code"""
        return getattr(self, '_fileName', None)

    @spiceFileName.setter
    def spiceFileName(self, value):
        self._fileName = value


class CreateConfigViewDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.mainLayout = QVBoxLayout()
        self.setWindowTitle("Create New Config View")
        self.setMinimumSize(360, 400)
        topCellGroup = QGroupBox("Top Cell")
        topCellLayout = QFormLayout()
        self.libraryNameEdit = edf.LongLineEdit()
        topCellLayout.addRow(edf.BoldLabel("Library:"), self.libraryNameEdit)
        self.cellNameEdit = edf.LongLineEdit()
        topCellLayout.addRow(edf.BoldLabel("Cell:"), self.cellNameEdit)
        self.viewNameCB = QComboBox()
        topCellLayout.addRow(edf.BoldLabel("View:"), self.viewNameCB)
        topCellGroup.setLayout(topCellLayout)
        self.mainLayout.addWidget(topCellGroup)
        viewGroup = QGroupBox("Switch/Stop Views")
        viewGroupLayout = QFormLayout()
        viewGroup.setLayout(viewGroupLayout)
        self.switchViews = edf.LongLineEdit()
        viewGroupLayout.addRow(edf.BoldLabel("View List:"), self.switchViews)
        self.stopViews = edf.LongLineEdit()
        viewGroupLayout.addRow(edf.BoldLabel("Stop List:"), self.stopViews)
        self.mainLayout.addWidget(viewGroup)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)


class AppProperties(QDialog):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(parent)
        self.setMinimumSize(750, 550)
        self.setWindowTitle("Revolution EDA Options")
        mainLayout = QVBoxLayout()
        mainLayout.setStretch(0, 2)
        mainLayout.setStretch(1, 2)
        filePathsGroup = QGroupBox("Paths")
        filePathsLayout = QVBoxLayout()
        filePathsLayout.setSpacing(20)

        rootPathDialogLayout = QHBoxLayout()
        rootPathDialogLayout.addWidget(edf.BoldLabel("Root (Run) Path:"), 2)
        self.rootPathEdit = edf.LongLineEdit()
        rootPathDialogLayout.addWidget(self.rootPathEdit, 5)
        self.rootPathButton = QPushButton("...")
        self.rootPathButton.clicked.connect(self.onRootPathButtonClicked)
        filePathsLayout.addLayout(rootPathDialogLayout)
        rootPathDialogLayout.addWidget(self.rootPathButton, 1)
        simInPathDialogLayout = QHBoxLayout()
        simInPathDialogLayout.addWidget(edf.BoldLabel("PDK Path:"), 2)
        self.simInpPathEdit = edf.LongLineEdit()
        simInPathDialogLayout.addWidget(self.simInpPathEdit, 5)
        self.simInpPathButton = QPushButton("...")
        self.simInpPathButton.clicked.connect(self.onSimInpPathButtonClicked)
        simInPathDialogLayout.addWidget(self.simInpPathButton, 1)
        filePathsLayout.addLayout(simInPathDialogLayout)
        simOutPathDialogLayout = QHBoxLayout()
        simOutPathDialogLayout.addWidget(edf.BoldLabel("Simulation Outputs Path:"), 2)
        self.simOutPathEdit = edf.LongLineEdit()
        simOutPathDialogLayout.addWidget(self.simOutPathEdit, 5)
        self.simOutPathButton = QPushButton("...")
        self.simOutPathButton.clicked.connect(self.onSimOutPathButtonClicked)
        simOutPathDialogLayout.addWidget(self.simOutPathButton, 1)
        filePathsLayout.addLayout(simOutPathDialogLayout)
        pluginsPathDialogLayout = QHBoxLayout()
        pluginsPathDialogLayout.addWidget(edf.BoldLabel("Plugins Path:"), 2)
        self.pluginsPathEdit = edf.LongLineEdit()
        pluginsPathDialogLayout.addWidget(self.pluginsPathEdit, 5)
        self.pluginsPathButton = QPushButton("...")
        self.pluginsPathButton.clicked.connect(self.onPluginsPathButtonClicked)
        pluginsPathDialogLayout.addWidget(self.pluginsPathButton, 1)
        filePathsLayout.addLayout(pluginsPathDialogLayout)
        vaModulePathDialogLayout = QHBoxLayout()
        vaModulePathDialogLayout.addWidget(edf.BoldLabel("Verilog-A Module Path:"), 2)
        self.vaModulePathEdit = edf.LongLineEdit()
        vaModulePathDialogLayout.addWidget(self.vaModulePathEdit, 5)
        self.vaModulePathButton = QPushButton("...")
        self.vaModulePathButton.clicked.connect(self.onVaModulePathButtonClicked)
        vaModulePathDialogLayout.addWidget(self.vaModulePathButton, 1)
        filePathsLayout.addLayout(vaModulePathDialogLayout)
        filePathsGroup.setLayout(filePathsLayout)
        mainLayout.addWidget(filePathsGroup)
        switchViewsGroup = QGroupBox("Switch and Stop Views")
        switchViewsLayout = QFormLayout()
        switchViewsLayout.setSpacing(20)
        self.switchViewsEdit = edf.LongLineEdit()
        switchViewsLayout.addRow(edf.BoldLabel("Switch Views:"), self.switchViewsEdit)
        self.stopViewsEdit = edf.LongLineEdit()
        switchViewsLayout.addRow(edf.BoldLabel("Stop Views:"), self.stopViewsEdit)
        switchViewsGroup.setLayout(switchViewsLayout)
        mainLayout.addWidget(switchViewsGroup)
        performanceGroup = QGroupBox("Performance Settings")
        performanceLayout = QFormLayout()
        self.threadPoolEdit = edf.ShortLineEdit()
        performanceLayout.addRow(edf.BoldLabel("Thread Pool Max Count:"),
                                 self.threadPoolEdit)
        performanceGroup.setLayout(performanceLayout)
        mainLayout.addWidget(performanceGroup)
        saveGroupBox = QGroupBox("Save Options")
        saveGBLayout = QVBoxLayout()
        self.optionSaveBox = QCheckBox("Save options to configuration file?")
        saveGBLayout.addWidget(self.optionSaveBox)
        saveGroupBox.setLayout(saveGBLayout)
        mainLayout.addWidget(saveGroupBox)
        mainLayout.addSpacing(20)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)

    def onRootPathButtonClicked(self):
        self.rootPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Root run path:")
        )

    def onSimOutPathButtonClicked(self):
        self.simOutPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Simulation Outputs path:")
        )

    def onSimInpPathButtonClicked(self):
        self.simInpPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Simulation Inputs (PDK) path:")
        )

    def onPluginsPathButtonClicked(self):
        self.pluginsPathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Plugins path:")
        )

    def onVaModulePathButtonClicked(self):
        self.vaModulePathEdit.setText(
            QFileDialog.getExistingDirectory(self, caption="Verilog-a Modules path:")
        )


class LibraryPathsModel(QStandardItemModel):
    def __init__(self, libraryDict):
        super().__init__()
        self.libraryDict = libraryDict
        self.setHorizontalHeaderLabels(["Library Name", "Library Path"])
        for key, value in self.libraryDict.items():
            libName = QStandardItem(key)
            libPath = QStandardItem(str(value))
            self.appendRow([libName, libPath])
        self.appendRow([QStandardItem("Right click here..."), QStandardItem("")])


class LibraryPathsTableView(QTableView):
    def __init__(self, model, logger):
        super().__init__()
        self.model = model
        self.logger = logger
        self.setModel(self.model)
        self.setShowGrid(True)
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 400)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(QFileDialog.Directory)
        self.libNameEditList = list()
        self.libPathEditList = list()
        for row in range(self.model.rowCount()):
            self.libPathEditList.append(edf.LongLineEdit())
            self.setIndexWidget(self.model.index(row, 1), self.libPathEditList[-1])
            self.libPathEditList[-1].setText(self.model.item(row, 1).text())

    def contextMenuEvent(self, event) -> None:
        self.menu = QMenu(self)
        try:
            selectedIndex = self.selectedIndexes()[0]
        except IndexError:
            self.model.appendRow([QStandardItem("Click here..."), QStandardItem("")])
            selectedIndex = self.model.index(0, 0)
        removePathAction = self.menu.addAction("Remove Path")
        removePathAction.triggered.connect(
            lambda: self.removeLibraryPath(selectedIndex)
        )
        addPathAction = self.menu.addAction("Add Library Path")
        addPathAction.triggered.connect(lambda: self.addLibraryPath(selectedIndex))
        self.menu.exec(event.globalPos())

    def removeLibraryPath(self, index):
        self.model.takeRow(index.row())
        self.logger.info("Removed Library Path.")

    def addLibraryPath(self, index):
        row = index.row()
        self.selectRow(row)
        self.fileDialog.exec()
        if self.fileDialog.selectedFiles():
            self.selectedDirectory = QDir(self.fileDialog.selectedFiles()[0])
        self.model.insertRow(
            row,
            [
                QStandardItem(self.selectedDirectory.dirName()),
                QStandardItem(self.selectedDirectory.absolutePath()),
            ],
        )


class LibraryPathEditorDialog(QDialog):
    def __init__(self, parent, libraryDict: dict):
        super().__init__(parent)
        self.parent = parent
        self.logger = self.parent.logger
        self.libraryDict = libraryDict
        self.setWindowTitle("Library Paths Dialogue")
        self.setMinimumSize(700, 300)
        self.mainLayout = QVBoxLayout()
        self.pathsBox = QGroupBox()
        self.boxLayout = QVBoxLayout()
        self.pathsBox.setLayout(self.boxLayout)
        self.pathsModel = LibraryPathsModel(self.libraryDict)
        self.tableView = LibraryPathsTableView(self.pathsModel, self.logger)
        self.boxLayout.addWidget(self.tableView)
        self.mainLayout.addWidget(self.pathsBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)


class KlayoutLaypImportDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.logger = self.parent.logger

        self.setWindowTitle("KLayout Layout Layers File Importer")
        self.setMinimumSize(500, 250)
        mainLayout = QVBoxLayout()
        fileBox = QGroupBox("Import KLayout Layer Properties File")
        fileBoxLayout = QVBoxLayout()
        inputFileDialogLayout = QHBoxLayout()
        inputFileDialogLayout.addWidget(edf.BoldLabel("Layer Properties File:"))
        self.laypFileEdit = edf.LongLineEdit()
        inputFileDialogLayout.addWidget(self.laypFileEdit)
        self.laypFileButton = QPushButton("...")
        self.laypFileButton.clicked.connect(self.onFileButtonClicked)
        inputFileDialogLayout.addWidget(self.laypFileButton)
        fileBoxLayout.addLayout(inputFileDialogLayout)
        fileBoxLayout.addSpacing(20)
        outputFileDialogLayout = QHBoxLayout()
        outputFileDialogLayout.addWidget(edf.BoldLabel("Output File Directory:"))
        self.outputFileEdit = edf.LongLineEdit()
        outputFileDialogLayout.addWidget(self.outputFileEdit)
        self.outputFileButton = QPushButton("...")
        self.outputFileButton.clicked.connect(self.onDirButtonClicked)
        outputFileDialogLayout.addWidget(self.outputFileButton)
        fileBoxLayout.addLayout(outputFileDialogLayout)
        fileBox.setLayout(fileBoxLayout)
        mainLayout.addWidget(fileBox)
        mainLayout.addSpacing(20)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)

    def onFileButtonClicked(self):
        fileDialog = QFileDialog()
        fileDialog.setNameFilter("Layout Properties files (*.lyp)")
        laypFileName = fileDialog.getOpenFileName(
            self, caption="Select LayoutProperties file.", dir=str(pathlib.Path.cwd()),
            filter="Layout Properties files (*.lyp)")[0]
        if laypFileName:
            self.laypFileEdit.setText(laypFileName)

    def onDirButtonClicked(self):
        dirDialog = QFileDialog()
        dirDialog.setFileMode(QFileDialog.Directory)
        dirDialog.setOption(QFileDialog.ShowDirsOnly)
        dirDialog.exec()
        if dirDialog.selectedFiles():
            self.outputFileEdit.setText(dirDialog.selectedFiles()[0])


class KlayoutLaytImportDialogue(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.logger = self.parent.logger

        self.setWindowTitle("KLayout Layout Technology File Importer")
        self.setMinimumSize(500, 100)
        mainLayout = QVBoxLayout()
        fileBox = QGroupBox("Import KLayout Technology File")
        fileDialogLayout = QHBoxLayout()
        fileDialogLayout.addWidget(edf.BoldLabel("Technology Properties File:"))
        self.laytFileEdit = edf.LongLineEdit()
        fileDialogLayout.addWidget(self.laytFileEdit)
        self.laytFileButton = QPushButton("...")
        self.laytFileButton.clicked.connect(self.onFileButtonClicked)
        fileDialogLayout.addWidget(self.laytFileButton)
        fileBox.setLayout(fileDialogLayout)
        mainLayout.addWidget(fileBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)

    def onFileButtonClicked(self):
        fileDialog = QFileDialog()
        fileDialog.setNameFilter("Layout Properties files (*.lyt)")
        laytFileName = fileDialog.getOpenFileName(
            self, caption="Select LayoutProperties file.", dir=str(pathlib.Path.cwd()),
            filter="Layout Properties files (*.lyt)")[0]
        if laytFileName:
            self.laytFileEdit.setText(laytFileName)


class XschemSymIimportDialogue(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.parent = parent
        self.logger = self.parent.logger
        self.model = model
        # print(self.model)
        self.setWindowTitle("Xschem Symbol File Importer")
        self.setMinimumSize(500, 300)
        mainLayout = QVBoxLayout()
        fileBox = QGroupBox("Import Xschem Symbol Files")
        fileDialogLayout = QHBoxLayout()
        fileDialogLayout.addWidget(edf.BoldLabel("Xschem Symbol Files:"))
        self.symFileEdit = edf.LongLineEdit()
        fileDialogLayout.addWidget(self.symFileEdit)
        self.symFileButton = QPushButton("...")
        self.symFileButton.clicked.connect(self.onFileButtonClicked)
        fileDialogLayout.addWidget(self.symFileButton)
        fileBox.setLayout(fileDialogLayout)
        mainLayout.addWidget(fileBox)
        libraryBox = QGroupBox('Select Library')
        libraryBoxLayout = QFormLayout()
        self.libNamesCB = QComboBox()
        self.libNamesCB.setModel(self.model)
        self.libNamesCB.setModelColumn(0)
        self.libNamesCB.setCurrentIndex(0)
        libraryBoxLayout.addRow(edf.BoldLabel("Library:"), self.libNamesCB)
        libraryBox.setLayout(libraryBoxLayout)
        mainLayout.addWidget(libraryBox)
        parameterBox = QGroupBox('Import Parameters')
        parameterBoxLayout = QFormLayout()
        self.scaleEdit = edf.LongLineEdit()
        self.scaleEdit.setText('4')
        parameterBoxLayout.addRow(edf.BoldLabel("Scale Factor"), self.scaleEdit)
        parameterBox.setLayout(parameterBoxLayout)
        mainLayout.addWidget(parameterBox)
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)
        self.setLayout(mainLayout)

    def onFileButtonClicked(self):
        fileDialog = QFileDialog()
        fileDialog.setNameFilter("Xschem Symbol Files (*.sym)")
        fileDialog.setFileMode(QFileDialog.ExistingFiles)
        if fileDialog.exec():
            symFileNames = fileDialog.selectedFiles()
            if symFileNames:
                self.symFileEdit.setText(', '.join(symFileNames))


class FileInfoDialogue(QDialog):
    def __init__(self, filePath: pathlib.Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Information")
        self.setMinimumSize(500, 200)
        layout = QFormLayout(self)
        # Get file stats
        stats = filePath.stat()
        created = datetime.datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.datetime.fromtimestamp(stats.st_mtime)
        size = stats.st_size

        layout.addRow("File:", QLabel(filePath.name))
        layout.addRow("Path:", QLabel(str(filePath.absolute())))
        layout.addRow("Size:", QLabel(f"{size:,} bytes"))
        layout.addRow("Created:", QLabel(created.strftime("%Y-%m-%d %H:%M:%S")))
        layout.addRow("Modified:", QLabel(modified.strftime("%Y-%m-%d %H:%M:%S")))
        layout.addRow("Accessed:", QLabel(
            datetime.datetime.fromtimestamp(stats.st_atime).strftime("%Y-%m-%d %H:%M:%S")))
        layout.addRow("Permissions:", QLabel(oct(stats.st_mode)[-3:]))
        # layout.addRow("Owner:", QLabel(str(stats.st_uid)))
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)
