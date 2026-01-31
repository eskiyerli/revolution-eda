import json
import pathlib
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QDialog, QApplication, )

import revedaEditor.gui.fileDialogues as fd
from revedaEditor.backend import libraryModelView as lmview, hdlBackEnd as hdl, \
    dataDefinitions as ddef, libraryMethods as libm, libBackEnd as scb
from revedaEditor.fileio.createSymbols import createVaSymbol


def importVerilogaModule(viewT: ddef.viewTuple, filePath: str):
    appMainW = QApplication.instance().mainW
    library_model = appMainW.libraryBrowser.designView.libraryModel
    # Open the import dialog
    importDlg = fd.importVerilogaCellDialogue(library_model, appMainW.libraryBrowser)
    importDlg.vaFileEdit.setText(filePath)
    if viewT.libraryName:
        importDlg.libNamesCB.setCurrentText(viewT.libraryName)
    if viewT.cellName:
        importDlg.cellNamesCB.setCurrentText(viewT.cellName)
    if viewT.viewName:
        importDlg.vaViewName.setText(viewT.viewName)
    else:
        # Set the default view name in the dialog
        importDlg.vaViewName.setText("veriloga")
    # Execute the import dialog and check if it was accepted
    if importDlg.exec() == QDialog.DialogCode.Accepted:
        # Create the Verilog-A object from the file path
        imported_va_obj = hdl.verilogaC(pathlib.Path(importDlg.vaFileEdit.text()))

        # Create the Verilog-A view item tuple
        vaViewItemTuple = createVaView(appMainW.libraryBrowser, importDlg, library_model,
                                       imported_va_obj)

        # Check if the symbol checkbox is checked
        if importDlg.symbolCheckBox.isChecked():
            # Create the Verilog-A symbol
            createVaSymbol(appMainW.libraryBrowser, vaViewItemTuple, appMainW.libraryDict,
                           appMainW.libraryBrowser,
                           imported_va_obj, )


def createVaView(parent: QMainWindow, importDlg: QDialog,
                 libraryModel: lmview.designLibrariesModel,
                 importedVaObj: hdl.verilogaC, ) -> ddef.viewItemTuple:
    """
    Create a new Verilog-A view.

    Args:
        parent (QMainWindow): The parentW window.
        importDlg (QDialog): The import dialog window.
        libraryModel (edw.designLibrariesModel): The model for the design libraries.
        importedVaObj (hdl.verilogaC): The imported Verilog-A object.

    Returns:
        tuple: A tuple containing the library item, cell item, and Verilog-A item.
    """
    # Get the file path of the imported Verilog-A file
    importedVaFilePathObj = pathlib.Path(importDlg.vaFileEdit.text())

    # Get the selected library item
    libItem = libm.getLibItem(libraryModel, importDlg.libNamesCB.currentText())
    libItemRow = libItem.row()

    # Get the cell names in the selected library
    libCellNames = [libraryModel.item(libItemRow).child(i).cellName for i in
                    range(libraryModel.item(libItemRow).rowCount())]

    # Get the selected cell name
    cellName = importDlg.cellNamesCB.currentText().strip()

    # If the cell name is not in the library and is not empty, create a new cell
    if cellName not in libCellNames and cellName != "":
        scb.createCell(parent, libraryModel, libItem, cellName)

    # Get the cell item
    cellItem = libm.getCellItem(libItem, cellName)

    # Generate the new file path for the Verilog-A file
    newVaFilePathObj = cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
        importedVaFilePathObj.name)

    # Create the Verilog-A item view
    vaItem = scb.createCellView(parent, importDlg.vaViewName.text(), cellItem)

    # Create a temporary copy of the imported Verilog-A file
    tempFilePathObj = importedVaFilePathObj.with_suffix(".temp")
    shutil.copy(importedVaFilePathObj, tempFilePathObj)

    # Copy the temporary file to the new file path
    shutil.copy(tempFilePathObj, newVaFilePathObj)

    # Remove the temporary file
    tempFilePathObj.unlink()

    # Create a list of items to be stored in the Verilog-A item data
    items = list()
    items.insert(0, {"cellView": "veriloga"})
    items.insert(1, {"filePath": str(newVaFilePathObj.name)})
    items.insert(2, {"vaModule": importedVaObj.vaModule})

    # Write the items to the Verilog-A item data file
    with vaItem.data(Qt.ItemDataRole.UserRole + 2).open(mode="w") as f:
        json.dump(items, f, indent=4)

    # Return the tuple of library item, cell item, and Verilog-A item
    return ddef.viewItemTuple(libItem, cellItem, vaItem)
