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
#    consideration (including without limitation fees for hosting) a product or service
#    whose value derives, entirely or substantially, from the functionality of the Software.
#    Any license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#


import json
import logging
import pathlib
import shutil
from typing import List

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (QAction, QStandardItemModel, QStandardItem, )
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QMenu, QMessageBox, QTreeView,
                               QWidget, QApplication, QListView, QHBoxLayout, QVBoxLayout,
                               QLabel, )

import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libBackEnd as libb
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.layoutDialogues as ldlg
import revedaEditor.gui.textEditor as ted
from revedaEditor.gui.configEditor import configEditor


class BaseDesignLibrariesView(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self._app = QApplication.instance()
        self.libBrowsW = self.parentWidget().parentWidget()
        self.appMainW = self.libBrowsW.appMainW
        self.libraryDict = self.appMainW.libraryDict  # type: dict
        self.cellViews = self.libBrowsW.cellViews  # type: list
        self.openViews = self.appMainW.openViews  # type: dict
        self.logger = logging.getLogger("reveda")

        # Common selection tracking
        self.selectedLib = None
        self.selectedCell = None
        self.selectedView = None

        # Initialize the model (to be implemented by child classes)
        self.libraryModel = designLibrariesModel(self.libraryDict)

    def removeLibrary(self, selectedLib: libb.libraryItem):
        try:
            button = QMessageBox.question(self, "Library Deletion",
                                          "Are you sure to delete this library? This action cannot be undone.", )
            if button == QMessageBox.Yes:
                self.libraryModel.removeLibraryFromModel(selectedLib)
                self.libraryDict.pop(selectedLib.libraryName, None)
                self.reworkDesignLibrariesView(self.libraryDict)
                self.libBrowsW.writeLibDefFile(self.libraryDict, self.libBrowsW.libFilePath)
        except Exception as e:
            self.logger.error(f"Error removing library: {e}")

    def renameLib(self, selectedLib: libb.libraryItem):
        try:
            oldLibraryName = selectedLib.libraryName
            dlg = fd.renameLibDialog(self, oldLibraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                newLibraryName = dlg.newLibraryName.text().strip()
                libraryItem = libm.getLibItem(self.libraryModel, oldLibraryName)
                oldLibraryPath = libraryItem.data(Qt.ItemDataRole.UserRole + 2)
                self.libraryModel.removeRow(libraryItem.row())
                newLibraryPath = oldLibraryPath.parent.joinpath(newLibraryName)
                oldLibraryPath.rename(newLibraryPath)
                self.libraryDict.pop(oldLibraryName)
                self.libraryDict[newLibraryName] = pathlib.Path(newLibraryPath)
                self.reworkDesignLibrariesView(self.libraryDict)
                self.libBrowsW.writeLibDefFile(self.libraryDict, self.libBrowsW.libFilePath)
        except Exception as e:
            self.logger.error(f"Error renaming library: {e}")

    def openView(self, selectedViewItem: libb.viewItem):
        try:
            cellItem = selectedViewItem.parent()
            self.openCellView(selectedViewItem)
        except Exception as e:
            self.logger.error(f"Error opening view: {e}")

    def createNewCellView(self, libItem, cellItem, viewItem):
        from revedaEditor.gui.editorFactory import EditorFactory

        viewTuple = ddef.viewTuple(libItem.libraryName, cellItem.cellName,
                                   viewItem.viewName)

        if viewItem.viewType in ["schematic", "symbol", "layout"]:
            editor = EditorFactory.createEditor(viewItem.viewType, viewItem,
                                                self.libraryDict,
                                                self)
            self.appMainW.openViews[viewTuple] = editor
            if hasattr(editor, "loadSchematic"):
                editor.loadSchematic()
            elif hasattr(editor, "loadSymbol"):
                editor.loadSymbol()
            elif hasattr(editor, "loadLayout"):
                editor.loadLayout()
            editor.show()
        elif viewItem.viewType == "veriloga":
            editor = ted.verilogaEditor(
                viewItem.viewPath.parent / f"{cellItem.cellName}.va")
            editor.cellViewTuple = viewTuple
            editor.closedSignal.connect(self.verilogaEditFinished)
            self.appMainW.openViews[viewTuple] = editor
            editor.show()
        elif viewItem.viewType == "spice":
            editor = ted.spiceEditor(viewItem.viewPath)
            editor.cellViewTuple = viewTuple
            editor.closedSignal.connect(self.spiceEditFinished)
            self.appMainW.openViews[viewTuple] = editor
            editor.show()
        # elif viewItem.viewType == "revbench":
        #     self.openRevbenchWindow(libItem, cellItem, viewItem)
        elif viewItem.viewType == "config":
            schViewsList = [cellItem.child(row).viewName for row in
                            range(cellItem.rowCount()) if
                            cellItem.child(row).viewType == "schematic"]
            dlg = fd.createConfigViewDialogue(self.appMainW)
            dlg.libraryNameEdit.setText(libItem.libraryName)
            dlg.cellNameEdit.setText(cellItem.cellName)
            dlg.viewNameCB.addItems(schViewsList)
            dlg.switchViews.setText(", ".join(self.appMainW.switchViewList))
            dlg.stopViews.setText(", ".join(self.appMainW.stopViewList))
            if dlg.exec() == QDialog.DialogCode.Accepted:
                from revedaEditor.gui.configEditor import createNewConfigView
                configWindow = createNewConfigView(cellItem, viewItem, dlg,
                                                   self.libraryDict,
                                                   self)
                self.appMainW.openViews[viewTuple] = configWindow
                configWindow.show()
        elif viewItem.viewType == "pcell":
            dlg = ldlg.pcellLinkDialogue(self.appMainW, viewItem)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                items = [{"cellView": "pcell"}, {"reference": dlg.pcellCB.currentText()}]
                with viewItem.data(Qt.ItemDataRole.UserRole + 2).open(
                        mode="w+") as pcellFile:
                    json.dump(items, pcellFile, indent=4)
            else:
                try:
                    viewItem.data(Qt.ItemDataRole.UserRole + 2).unlink()
                    viewItem.parent().removeRow(viewItem.row())
                except OSError as e:
                    self.logger.warning(f"Error:{e.strerror}")
        else:
            self._app.pluginsObj.openCellView(viewItem)

    def reworkDesignLibrariesView(self, libraryDict: dict):
        """
        To be implemented by child classes.
        """
        pass

    def _handle_spice_view(self, viewItem, openCellViewTuple):
        """Handle spice view opening."""
        with open(viewItem.viewPath) as tempFile:
            items = json.load(tempFile)
        if items[1]["filePath"]:
            spiceFilePathObj = (
                viewItem.parent().data(Qt.ItemDataRole.UserRole + 2).joinpath(
                    items[1]["filePath"]))
            spiceEditor = ted.spiceEditor(spiceFilePathObj)
            self.appMainW.openViews[openCellViewTuple] = spiceEditor
            spiceEditor.cellViewTuple = openCellViewTuple
            spiceEditor.closedSignal.connect(self.spiceEditFinished)
            spiceEditor.show()
        else:
            self.logger.warning("File path not defined.")

    def _handle_veriloga_view(self, viewItem, openCellViewTuple):
        """Handle veriloga view opening."""
        with open(viewItem.viewPath) as tempFile:
            items = json.load(tempFile)
        if items[1]["filePath"]:
            VerilogafilePathObj = (
                viewItem.parent().data(Qt.ItemDataRole.UserRole + 2).joinpath(
                    items[1]["filePath"]))
            verilogaEditor = ted.verilogaEditor(VerilogafilePathObj)
            self.appMainW.openViews[openCellViewTuple] = verilogaEditor
            verilogaEditor.cellViewTuple = openCellViewTuple
            verilogaEditor.closedSignal.connect(self.verilogaEditFinished)
            verilogaEditor.show()
        else:
            self.logger.warning("File path not defined.")

    def openCellView(self, viewItem: libb.viewItem):
        from revedaEditor.gui.editorFactory import EditorFactory
        if not viewItem:
            return
        cellItem = viewItem.parent()
        if not cellItem:
            return
        libItem = cellItem.parent()
        if not libItem:
            return

        viewName = viewItem.viewName
        cellName = cellItem.cellName
        libName = libItem.libraryName
        openCellViewTuple = ddef.viewTuple(libName, cellName, viewName)

        if openCellViewTuple in self.appMainW.openViews.keys():
            self.appMainW.openViews[openCellViewTuple].show()
            return openCellViewTuple

        view_type = viewItem.viewType

        # Handle standard editor types using factory
        if view_type in EditorFactory.getSupportedViewTypes():
            editor = EditorFactory.createEditor(view_type, viewItem, self.libraryDict,
                                                self)

            # Load content based on editor type - use view_type instead of hasattr
            if view_type == 'layout':
                editor.loadLayout()  # type: ignore[attr-defined]
            elif view_type == 'schematic':
                editor.loadSchematic()  # type: ignore[attr-defined]
            elif view_type == 'symbol':
                editor.loadSymbol()  # type: ignore[attr-defined]

            editor.show()

            # Fit items in view if available
            if hasattr(editor, 'centralW') and hasattr(editor.centralW, 'scene'):
                editor.centralW.scene.fitItemsInView()
            self.appMainW.openViews[openCellViewTuple] = editor

        # Handle special cases that require custom logic
        elif view_type == "config":
            editor = configEditor(viewItem, self.libraryDict,
                                  self)
            editor.loadConfig()
        elif view_type == "spice":
            editor = ted.spiceEditor(viewItem.viewPath)
            editor.cellViewTuple = openCellViewTuple
            editor.closedSignal.connect(self.spiceEditFinished)
            self.appMainW.openViews[openCellViewTuple] = editor
            editor.show()
        elif view_type == "veriloga":
            self._handle_veriloga_view(viewItem, openCellViewTuple)
        # elif view_type == "revbench":
        #     self._handle_revbench_view(viewItem, openCellViewTuple)
        else:
            self._app.pluginsObj.openCellView(viewItem)

        return openCellViewTuple

    def verilogaEditFinished(self, editor: ted.verilogaEditor):
        import revedaEditor.fileio.importVeriloga as imva
        imva.importVerilogaModule(editor.cellViewTuple, str(editor.filePathObj))
        # self.appMainW.openViews.pop(editor.cellViewTuple)

    def spiceEditFinished(self, editor: ted.spiceEditor):
        import revedaEditor.fileio.importSpice as imsp
        imsp.importSpiceSubckt(editor.cellViewTuple, str(editor.filePathObj))
        # self.appMainW.openViews.pop(editor.cellViewTuple)


class designLibrariesColumnView(BaseDesignLibrariesView):
    def __init__(self, parent):
        super().__init__(parent=parent)  # QTreeView

        # Create three list views with labels
        self.libsListView = QListView()

        self.libsListView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.libsListView.customContextMenuRequested.connect(self.libsListContextMenuEvent)
        self.cellsListView = QListView()
        self.cellsListView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cellsListView.customContextMenuRequested.connect(
            self.cellsListContextMenuEvent)
        self.viewsListView = QListView()
        self.viewsListView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.viewsListView.customContextMenuRequested.connect(
            self.viewsListContextMenuEvent)

        libsLabel = QLabel("**Libraries**")
        libsLabel.setTextFormat(Qt.MarkdownText)
        cellsLabel = QLabel("**Cells**")
        cellsLabel.setTextFormat(Qt.MarkdownText)
        viewsLabel = QLabel("**Cell Views**")
        viewsLabel.setTextFormat(Qt.MarkdownText)
        # Create a horizontal layout and add the list views to it
        layout = QHBoxLayout()

        # Create vertical layouts for each list with its label
        libsLayout = QVBoxLayout()
        libsLayout.addWidget(libsLabel)
        libsLayout.addWidget(self.libsListView)

        cellsLayout = QVBoxLayout()
        cellsLayout.addWidget(cellsLabel)
        cellsLayout.addWidget(self.cellsListView)

        viewsLayout = QVBoxLayout()
        viewsLayout.addWidget(viewsLabel)
        viewsLayout.addWidget(self.viewsListView)

        # Add layouts to main layout
        layout.addLayout(libsLayout)
        layout.addLayout(cellsLayout)
        layout.addLayout(viewsLayout)
        self.setLayout(layout)

        self.libsListView.setModel(self.libraryModel)
        # Connect selection signals
        self.libsListView.selectionModel().selectionChanged.connect(
            self.onLibsListSelection)

    def onLibsListSelection(self, selected, deselected):
        # Clear second and third lists
        self.cellsListView.setModel(None)
        self.viewsListView.setModel(None)

        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            return

        # Create new model for second list
        cellsModel = QStandardItemModel()
        cellsModel.setHorizontalHeaderLabels(["Cells"])
        cellsModel.setSortRole(Qt.ItemDataRole.UserRole + 3)

        # Get the selected item and its children
        self.selectedLib = self.libraryModel.itemFromIndex(indexes[0])

        children = [self.selectedLib.child(i) for i in range(self.selectedLib.rowCount())]
        if self.selectedLib and self.selectedLib.hasChildren():
            for cellItem in children:
                clonedCellItem = cellItem.clone()
                cellsModel.appendRow(clonedCellItem)

        self.cellsListView.setModel(cellsModel)
        # Connect second list selection after setting its model
        self.cellsListView.selectionModel().selectionChanged.connect(
            self.onCellsListSelection)

    def recursive_clone(self, item):
        """Recursively clone an item and all its children."""
        clonedItem = item.clone()
        # Store reference to original item
        clonedItem.setData(item,
                           Qt.ItemDataRole.UserRole + 10)  # Use a custom role to store the original item

        if item.hasChildren():
            for i in range(item.rowCount()):
                child = item.child(i)
                clonedChild = self.recursive_clone(child)
                clonedItem.appendRow(clonedChild)
        return clonedItem

    def onCellsListSelection(self, selected, deselected):
        # Clear third list
        self.viewsListView.setModel(None)

        # Get the selected index
        indexes = selected.indexes()
        if not indexes:
            return
        cellItem = (
            self.cellsListView.model().itemFromIndex(indexes[0]).data(
                Qt.ItemDataRole.UserRole + 10))
        # Create new model for third list
        viewsModel = self.createViewsListModel(cellItem=cellItem)
        self.viewsListView.setModel(viewsModel)
        # Connect third list selection after setting its model
        self.viewsListView.selectionModel().selectionChanged.connect(
            self.onViewsListSelection)

    def createViewsListModel(self, cellItem: libb.cellItem) -> QStandardItemModel:
        """
        Create a new model for the views list based on the selected cell item.
        """
        viewsModel = QStandardItemModel()
        viewsModel.setHorizontalHeaderLabels(["Cell Views"])
        viewsModel.setSortRole(Qt.ItemDataRole.UserRole + 3)

        if cellItem and cellItem.hasChildren():
            for i in range(cellItem.rowCount()):
                child = cellItem.child(i)
                cloned_child = child.clone()
                cloned_child.setData(child, Qt.ItemDataRole.UserRole + 10)
                viewsModel.appendRow(cloned_child)
        return viewsModel

    def onViewsListSelection(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            self.selectedView = self.viewsListView.model().itemFromIndex(indexes[0])

    def reworkDesignLibrariesView(self, libraryDict: dict):
        """
        Recreate library model from libraryDict.
        """
        # Disconnect existing selection signals
        try:
            self.libsListView.selectionModel().selectionChanged.disconnect()
        except:
            pass

        # Create new model and set it
        self.libraryModel = designLibrariesModel(libraryDict)
        self.libsListView.setModel(self.libraryModel)

        # Reconnect selection signals
        self.libsListView.selectionModel().selectionChanged.connect(
            self.onLibsListSelection)

        # Clear other views
        self.cellsListView.setModel(None)
        self.viewsListView.setModel(None)

        # Update library model reference in parentW
        self.libBrowsW.libraryModel = self.libraryModel

    def libsListContextMenuEvent(self, pos: QPoint):
        senderView = self.sender()
        menu = QMenu()
        index = senderView.indexAt(pos)
        if index.isValid():
            selectedLibItem = self.libsListView.model().itemFromIndex(index)
            menu.addAction(QAction("Rename Library", self,
                                   triggered=lambda: self.renameLib(selectedLibItem), ))
            menu.addAction(QAction("Remove Library", self,
                                   triggered=lambda: self.removeLibrary(selectedLibItem), ))
            menu.addAction(QAction("Create Cell", self,
                                   triggered=lambda: self.createCell(selectedLibItem), ))
            menu.addAction(QAction("File Information...", self,
                                   triggered=lambda: self.showItemFileInfo(
                                       selectedLibItem), ))
            menu.exec(senderView.viewport().mapToGlobal(
                pos))  # Use global position for context menu

    def cellsListContextMenuEvent(self, pos):
        senderView = self.sender()
        menu = QMenu()
        index = senderView.indexAt(pos)
        if index.isValid():
            selectedCloneCellItem = self.cellsListView.model().itemFromIndex(index)
            selectedCellItem = selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
            menu.addAction(QAction("Create CellView...", self,
                                   triggered=lambda: self.createCellView(
                                       selectedCloneCellItem), ))
            menu.addAction(QAction("Copy Cell...", self,
                                   triggered=lambda: self.copyCell(selectedCellItem), ))
            menu.addAction(QAction("Rename Cell...", self,
                                   triggered=lambda: self.renameCell(
                                       selectedCloneCellItem), ))
            menu.addAction(QAction("Delete Cell...", self,
                                   triggered=lambda: self.deleteCell(
                                       selectedCloneCellItem), ))
            menu.addAction(QAction("File Information...", self,
                                   triggered=lambda: self.showClonedItemFileInfo(
                                       selectedCloneCellItem), ))
            menu.exec(senderView.viewport().mapToGlobal(
                pos))  # Use global position for context menu

    def viewsListContextMenuEvent(self, pos):
        senderView = self.sender()
        menu = QMenu()
        index = senderView.indexAt(pos)
        if index.isValid():
            selectedCloneViewItem = self.viewsListView.model().itemFromIndex(index)
            selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
            menu.addAction(QAction("Open View", self,
                                   triggered=lambda: self.openView(selectedViewItem)))
            menu.addAction(QAction("Copy View...", self, triggered=lambda: self.copyView(
                selectedCloneViewItem), ))
            menu.addAction(QAction("Rename View...", self,
                                   triggered=lambda: self.renameView(
                                       selectedCloneViewItem), ))
            menu.addAction(QAction("Delete View...", self,
                                   triggered=lambda: self.deleteView(
                                       selectedCloneViewItem), ))
            menu.addAction(QAction("File Information...", self,
                                   triggered=lambda: self.showClonedItemFileInfo(
                                       selectedCloneViewItem), ))
            menu.exec(senderView.viewport().mapToGlobal(
                pos))  # Use global position for context menu

    def createCell(self, selectedLib: libb.libraryItem):
        try:
            dlg = fd.createCellDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedLib.libraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                cellName = dlg.cellCB.currentText()
                if cellName.strip() != "":
                    selectedLib = libm.getLibItem(self.libraryModel,
                                                  dlg.libNamesCB.currentText())
                    newCellItem = libb.createCell(self, selectedLib, cellName)
                    if newCellItem:
                        # add now a clone of newCellItem to temporary cellListModel
                        cloneItem = newCellItem.clone()
                        self.cellsListView.model().appendRow(cloneItem)
                else:
                    self.logger.error("Please enter a cell name.")
        except OSError as e:
            self.logger.warning(f"Error creating cell: {e}")

    def copyCell(self, selectedCellItem: libb.cellItem):
        try:
            parentLib: libb.libraryItem = selectedCellItem.parent()
            dlg = fd.copyCellDialog(self)
            dlg.libraryCB.setModel(self.libraryModel)
            dlg.libraryCB.setCurrentText(parentLib.libraryName)
            pass
            if dlg.exec() == QDialog.DialogCode.Accepted:
                success, newCellItem = libb.copyCell(self, self.libraryModel,
                                                     selectedCellItem, dlg.copyName.text(),
                                                     dlg.selectedLibPath, )
                if success:
                    cloneItem = newCellItem.clone()
                    if selectedCellItem.hasChildren():
                        for i in range(selectedCellItem.rowCount()):
                            child = selectedCellItem.child(i)
                            clonedChild = child.clone()
                            cloneItem.appendRow(clonedChild)
                    self.cellsListView.model().appendRow(cloneItem)
                else:
                    self.logger.error("Failed to copy cell.")
        except OSError as e:
            self.logger.warning(f"Error copying cell: {e}")

    def renameCell(self, cloneCellItem: libb.cellItem):
        try:
            oldName = cloneCellItem.cellName
            cellItem = cloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
            dlg = fd.renameCellDialog(self, cellItem)
            libName = cellItem.parent().libraryName
            if dlg.exec() == QDialog.DialogCode.Accepted:
                newName = dlg.nameEdit.text().strip()
                libb.renameCell(self, cloneCellItem, newName)
                # update the original cell item
                libb.renameCell(self, cellItem, dlg.nameEdit.text().strip(), )
                updateJSONFieldInCell(self.libraryModel, libName, 'cell', oldName, newName)
                self.logger.info(f"Renamed {oldName} to {newName}")
        except OSError as e:
            self.logger.warning(f"Error renaming cell: {e}")

    def deleteCell(self, selectedCloneCellItem: libb.cellItem):
        try:
            originalCell = selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
            shutil.rmtree(selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 2))
            self.libraryModel.removeRow(originalCell.row())
            if self.cellsListView.model():
                self.cellsListView.model().removeRow(selectedCloneCellItem.row())
            self.logger.info(f"Cell {originalCell.cellName} deleted.")
            self.reworkDesignLibrariesView(self.libraryModel.libraryDict)

        except OSError as e:
            self.logger.warning(f"Error deleting cell: {e}")

    def copyView(self, selectedCloneViewItem: libb.viewItem):
        selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
        dlg = fd.copyViewDialog(self, self.libraryModel)
        dlg.libNamesCB.setCurrentText(selectedViewItem.parent().parent().libraryName)
        dlg.cellCB.setCurrentText(selectedViewItem.parent().cellName)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        if selectedViewItem.data(Qt.ItemDataRole.UserRole + 1) != "view":
            self.logger.error("Selected item is not a view.")
            return

        viewPath = selectedViewItem.data(Qt.ItemDataRole.UserRole + 2)
        libName = dlg.libNamesCB.currentText()
        cellName = dlg.cellCB.currentText()
        newViewName = dlg.viewName.text().strip()

        selectedLibItem = libm.getLibItem(self.libraryModel, libName)
        if not selectedLibItem:
            self.logger.error("Selected library not found.")
            return

        # Find or create cell
        cellItem = libm.getCellItem(selectedLibItem, cellName)  # noqa: F811
        if not cellItem:
            cellItem = libb.createCell(self.libBrowsW, self.libraryModel, selectedLibItem,
                                       cellName)

        # Check if view already exists
        if any(child.viewName == newViewName for child in
               (cellItem.child(row) for row in range(cellItem.rowCount()))):
            self.logger.warning("View already exists. Delete cellview and try again.")
            return

        newViewPath = cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
            f"{newViewName}.json")
        try:
            newViewPath.parent.mkdir(parents=True, exist_ok=True)
            newViewItem = libb.viewItem(newViewPath)
            shutil.copy(viewPath, newViewPath)
            cellItem.appendRow(newViewItem)
            viewsModel = self.createViewsListModel(cellItem)
            self.viewsListView.setModel(viewsModel)
            self.logger.info(f"View {newViewName} copied successfully.")
        except Exception as e:
            self.logger.error(f"Failed to copy view: {e}")

    def createCellView(self, selectedCloneCellItem: libb.cellItem):
        cellItem = selectedCloneCellItem.data(Qt.ItemDataRole.UserRole + 10)
        dlg = fd.newCellViewDialog(self, self.libraryModel)
        dlg.libNamesCB.setCurrentText(cellItem.parent().libraryName)
        dlg.cellCB.setCurrentText(cellItem.cellName)
        dlg.viewType.addItems(self.libBrowsW.cellViews)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.handleNewCellView(cellItem, dlg)

    def handleNewCellView(self, cellItem, dlg):
        viewName = dlg.viewName.text().strip()
        libItem = libm.getLibItem(self.libraryModel, dlg.libNamesCB.currentText())
        viewItem = libm.findViewItem(self.libraryModel, libItem.libraryName,
                                     cellItem.cellName, viewName)
        if viewItem:
            messagebox = QMessageBox(self)
            messagebox.setText("Cell view already exists.")
            messagebox.setIcon(QMessageBox.Warning)
            messagebox.setWindowTitle(f"{viewItem.viewName} already exists")
            messagebox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            messagebox.setDefaultButton(QMessageBox.Discard)
            result = messagebox.exec()
            if result == QMessageBox.Save:
                self.viewsListView.model().removeRow(viewItem.row())
                viewItem = libb.createCellView(self.appMainW, viewName, cellItem)
                self.createNewCellView(libItem, cellItem, viewItem)
                # Add the new view item to the views list
                cloneViewItem = viewItem.clone()
                self.viewsListView.model().appendRow(cloneViewItem)
        else:
            viewItem = libb.createCellView(self.appMainW, viewName, cellItem)
            # cellItem.appendRow(viewItem)
            self.createNewCellView(libItem, cellItem, viewItem)
            # Add the new view item to the views list
            cloneViewItem = viewItem.clone()
            self.viewsListView.model().appendRow(cloneViewItem)

    def renameView(self, selectedCloneViewItem: libb.viewItem):
        selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
        oldViewName = selectedViewItem.viewName
        cellItem = selectedViewItem.parent()  # noqa: F811
        dlg = fd.renameViewDialog(self.libBrowsW, oldViewName)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newName = dlg.newViewNameEdit.text()
            try:
                viewPathObj = selectedViewItem.data(Qt.ItemDataRole.UserRole + 2)
                newPathObj = viewPathObj.parent.joinpath(f"{newName}.json")
                if newPathObj.exists():
                    raise FileExistsError
                viewPathObj.rename(newPathObj)
                # Update the view item with the new path and name

                newViewItem = libb.viewItem(newPathObj)
                cellItem.appendRow(newViewItem)
                cellItem.removeRow(selectedViewItem.row())
                viewsModel = self.createViewsListModel(cellItem)
                self.viewsListView.setModel(viewsModel)
                self.logger.info(f"View {oldViewName} renamed to {newName}.")
            except FileExistsError:
                self.logger.error("Cellview exists.")

    def deleteView(self, selectedCloneViewItem: libb.viewItem):
        try:
            selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 2).unlink()
            selectedViewItem = selectedCloneViewItem.data(Qt.ItemDataRole.UserRole + 10)
            # Remove the original item from the model
            itemRow = selectedViewItem.row()
            cellItem = selectedViewItem.parent()
            cellItem.removeRow(itemRow)
            # Remove the cloned item from the view
            viewsModel = self.createViewsListModel(cellItem)
            self.viewsListView.setModel(viewsModel)
            self.logger.info(f"View {selectedViewItem.viewName} deleted.")
            self.reworkDesignLibrariesView(self.libraryModel.libraryDict)
        except FileNotFoundError:
            self.logger.warning("View file not found.")
        except PermissionError:
            self.logger.warning("Permission denied while deleting view.")

        except Exception as e:
            self.logger.warning(f"Error:{e}")

    def showClonedItemFileInfo(self, selectedCloneItem: libb.viewItem):
        selectedItem = selectedCloneItem.data(Qt.ItemDataRole.UserRole + 10)
        viewPath = selectedItem.data(Qt.ItemDataRole.UserRole + 2)
        if viewPath.exists():
            dlg = fd.fileInfoDialogue(viewPath, self.libBrowsW)
        dlg.exec()

    def showItemFileInfo(self, selectedItem: libb.viewItem):
        viewPath = selectedItem.data(Qt.ItemDataRole.UserRole + 2)
        if viewPath.exists():
            dlg = fd.fileInfoDialogue(viewPath, self.libBrowsW)
        dlg.exec()


class designLibrariesTreeView(BaseDesignLibrariesView):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.libraryModel.setSortRole(Qt.ItemDataRole.UserRole + 3)
        self.treeView = QTreeView()
        self.treeView.setModel(self.libraryModel)
        self.treeView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.treeView.setUniformRowHeights(True)
        # self.treeView.expandAll()
        layout = QVBoxLayout()
        layout.addWidget(self.treeView)
        self.setLayout(layout)

    def createCell(self, selectedLib: libb.libraryItem):
        try:
            dlg = fd.createCellDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedLib.libraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                cellName = dlg.cellCB.currentText()
                if cellName.strip() != "":
                    libb.createCell(self, selectedLib, cellName)
                else:
                    self.logger.error("Please enter a cell name.")
        except OSError as e:
            self.logger.warning(f"Error in creating cell:{e}")

    def copyCell(self, selectedCellItem: libb.cellItem):
        try:
            parentLibrary = selectedCellItem.parent()
            dlg = fd.copyCellDialog(self)
            dlg.libraryCB.setCurrentText(parentLibrary.libraryName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                success, newCellItem = libb.copyCell(self, self.libraryModel,
                                                     selectedCellItem, dlg.copyName.text(),
                                                     dlg.selectedLibPath, )
                if success:
                    self.logger.info("Cell copied successfully.")

        except OSError as e:
            self.logger.warning(f"Error in copying cell:{e}")

    def renameCell(self, selectedCell: libb.cellItem):
        try:
            dlg = fd.renameCellDialog(self, selectedCell)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                oldName = selectedCell.cellName
                libName = selectedCell.parent().libraryName
                success = libb.renameCell(self, dlg.cellItem, dlg.nameEdit.text())
                if success:
                    newName = selectedCell.cellName
                    self.logger.info(f"Cell {oldName} renamed to {dlg.nameEdit.text()}.")
                    updateJSONFieldInCell(self.libraryModel, libName, 'cell', oldName,
                                          newName)
        except OSError as e:
            self.logger.warning(f"Error in renaming cell:{e}")

    def deleteCell(self, selectedCell: libb.cellItem):
        try:
            shutil.rmtree(selectedCell.data(Qt.ItemDataRole.UserRole + 2))
            self.libraryModel.removeRow(selectedCell.row())
            self.logger.info(f"Cell {selectedCell.cellName} deleted.")
        except OSError as e:
            self.logger.warning(f"Error in deleting cell:{e}")

    def createCellView(self, selectedCell: libb.cellItem):
        try:
            dlg = fd.newCellViewDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedCell.parent().libraryName)
            dlg.cellCB.setCurrentText(selectedCell.cellName)
            dlg.viewType.addItems(self.libBrowsW.cellViews)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.handleNewCellView(selectedCell, dlg)
        except OSError as e:
            self.logger.warning(f"Error in creating cell view:{e}")

    def handleNewCellView(self, selectedCell, dlg):
        libItem = selectedCell.parent()
        cellItem = selectedCell
        viewName = dlg.viewName.text().strip()
        viewItem = libm.findViewItem(self.libraryModel, libItem.libraryName,
                                     cellItem.cellName, viewName)
        if viewItem:
            messagebox = QMessageBox(self)
            messagebox.setText("Cell view already exists.")
            messagebox.setIcon(QMessageBox.Warning)
            messagebox.setWindowTitle(f"{viewItem.viewName} already exists")
            messagebox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard)
            messagebox.setDefaultButton(QMessageBox.Discard)
            result = messagebox.exec()
            if result == QMessageBox.Save:
                cellItem.removeRow(viewItem.row())
                viewItem = libb.createCellView(self.libBrowsW, viewName, cellItem)
                cellItem.appendRow(viewItem)
                self.libBrowsW.createNewCellView(libItem, cellItem, viewItem)

        else:
            viewItem = libb.createCellView(self.appMainW, viewName.strip(), cellItem)
            cellItem.appendRow(viewItem)
            self.libBrowsW.createNewCellView(libItem, cellItem, viewItem)

    def copyView(self, selectedView: libb.viewItem):
        try:
            dlg = fd.copyViewDialog(self, self.libraryModel)
            dlg.libNamesCB.setCurrentText(selectedView.parent().parent().libraryName)
            dlg.cellCB.setCurrentText(selectedView.parent().cellName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                if selectedView.data(Qt.ItemDataRole.UserRole + 1) == "view":
                    viewPath = self.selectedItem.data(Qt.ItemDataRole.UserRole + 2)
                    selectedLibItem = libm.getLibItem(self.libraryModel,
                                                      dlg.libNamesCB.currentText())
                    cellName = dlg.cellCB.currentText()
                    libCellNames = [selectedLibItem.child(row).cellName for row in
                                    range(selectedLibItem.rowCount())]
                    if (
                            cellName in libCellNames):  # check if there is the cell in the library
                        cellItem = libm.getCellItem(selectedLibItem,
                                                    dlg.cellCB.currentText())
                    else:
                        cellItem = libb.createCell(self.libBrowsW, self.libraryModel,
                                                   selectedLibItem,
                                                   dlg.cellCB.currentText(), )
                    cellViewNames = [cellItem.child(row).viewName for row in
                                     range(cellItem.rowCount())]
                    newViewName = dlg.viewName.text()
                    if newViewName in cellViewNames:
                        self.logger.warning(
                            "View already exists. Delete cellview and try again.")
                    else:
                        newViewPath = cellItem.data(Qt.ItemDataRole.UserRole + 2).joinpath(
                            f"{newViewName}.json")
                        shutil.copy(viewPath, newViewPath)
                        cellItem.appendRow(libb.viewItem(newViewPath))
        except OSError as e:
            self.logger.warning(f"Error in copying view:{e}")

    def renameView(self, selectedView: libb.viewItem):
        try:
            oldViewName = selectedView.viewName
            dlg = fd.renameViewDialog(self.libBrowsW, oldViewName)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                newName = dlg.newViewNameEdit.text()
                try:
                    viewPathObj = selectedView.data(Qt.ItemDataRole.UserRole + 2)
                    newPathObj = selectedView.data(Qt.ItemDataRole.UserRole + 2).rename(
                        viewPathObj.parent.joinpath(f"{newName}.json"))
                    selectedView.parent().appendRow(libb.viewItem(newPathObj))
                    selectedView.parent().removeRow(selectedView.row())
                except FileExistsError:
                    self.logger.error("Cellview exists.")
        except OSError as e:
            self.logger.warning(f"Error in renaming view:{e}")

    def deleteView(self, selectedView: libb.viewItem):
        try:
            selectedView.data(Qt.ItemDataRole.UserRole + 2).unlink()
            itemRow = selectedView.row()
            parent = selectedView.parent()
            parent.removeRow(itemRow)
        except OSError as e:
            self.logger.warning(
                f"Error in removing item: {selectedView.viewName}:{e.strerror}")

    def reworkDesignLibrariesView(self, libraryDict: dict):
        """
        Recreate library model from libraryDict.
        """
        self.libraryModel = designLibrariesModel(libraryDict)
        self.setModel(self.libraryModel)
        self.libBrowsW.libraryModel = self.libraryModel

    def showFileInfo(self, selectedItem: libb.viewItem):
        viewPath = selectedItem.data(Qt.ItemDataRole.UserRole + 2)
        if viewPath.exists():
            dlg = fd.fileInfoDialogue(viewPath, self.libBrowsW)
        dlg.exec()

    # context menu
    # def contextMenuEvent(self, event):
    #     menu = QMenu(self)
    #     pos = event.pos()
    #     # Use self directly instead of self.sender()
    #     index = self.treeView.indexAt(pos)
    #     if index.isValid():
    #         selectedItem = self.libraryModel.itemFromIndex(index)
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        pos = self.treeView.mapFromGlobal(event.globalPos())
        index = self.treeView.indexAt(pos)
        if index.isValid():
            selectedItem = self.libraryModel.itemFromIndex(index)
            if selectedItem.data(Qt.ItemDataRole.UserRole + 1) == "library":
                menu.addAction(QAction("Rename Library", self.treeView,
                                       triggered=lambda: self.renameLib(selectedItem), ))
                menu.addAction(QAction("Remove Library", self.treeView,
                                       triggered=lambda: self.removeLibrary(
                                           selectedItem), ))
                menu.addAction(QAction("Create Cell", self.treeView,
                                       triggered=lambda: self.createCell(selectedItem), ))
            elif selectedItem.data(Qt.ItemDataRole.UserRole + 1) == "cell":
                menu.addAction(QAction("Create CellView...", self,
                                       triggered=lambda: self.createCellView(
                                           selectedItem), ))
                menu.addAction(QAction("Copy Cell...", self.treeView, triggered=lambda: (
                    self.copyCell(selectedItem.parent())), ))
                menu.addAction(QAction("Rename Cell...", self.treeView,
                                       triggered=lambda: self.renameCell(selectedItem), ))
                menu.addAction(QAction("Delete Cell...", self.treeView,
                                       triggered=lambda: self.deleteCell(selectedItem), ))
            elif selectedItem.data(Qt.ItemDataRole.UserRole + 1) == "view":
                menu.addAction(QAction("Open View", self.treeView,
                                       triggered=lambda: self.openView(selectedItem), ))
                menu.addAction(QAction("Copy View...", self,
                                       triggered=lambda: self.copyView(selectedItem), ))
                menu.addAction(QAction("Rename View...", self.treeView,
                                       triggered=lambda: self.renameView(selectedItem), ))
                menu.addAction(QAction("Delete View...", self.treeView,
                                       triggered=lambda: self.deleteView(selectedItem), ))
            menu.addAction(QAction("File Information...", self.treeView,
                                   triggered=lambda: self.showFileInfo(selectedItem), ))
            # Use global position for context menu
            menu.exec(event.globalPos())


class designLibrariesModel(QStandardItemModel):
    def __init__(self, libraryDict):
        self.libraryDict = libraryDict
        super().__init__()

        self.setHorizontalHeaderLabels(["Libraries"])
        self.initModel()
        self.logger = logging.getLogger("reveda")

    def initModel(self):
        for designPath in self.libraryDict.values():
            self.populateLibrary(designPath)

    def populateLibrary(self, designPath: pathlib.Path) -> None:  # designPath: Path
        """
        Populate library view.
        """
        if designPath.joinpath("reveda.lib").exists():
            libraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                cellItem = self.addCellToModel(designPath.joinpath(cell), libraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json"]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), cellItem)
                cellItem.sortChildren(0)
            libraryItem.sortChildren(0)

    def addLibraryToModel(self, designPath: pathlib.Path) -> libb.libraryItem:
        libraryEntry = libb.libraryItem(designPath)
        for row in range(self.invisibleRootItem().rowCount()):
            existingItem = self.invisibleRootItem().child(row)
            if existingItem.data(Qt.ItemDataRole.UserRole + 2) == designPath:
                self.logger.warning(f"Library {designPath} already exists in the model.")
                break
        else:
            self.invisibleRootItem().appendRow(libraryEntry)
        return libraryEntry

    def removeLibraryFromModel(self, libraryItem: libb.libraryItem) -> None:
        shutil.rmtree(libraryItem.data(Qt.ItemDataRole.UserRole + 2), ignore_errors=True)
        self.invisibleRootItem().removeRow(libraryItem.row())

    def addCellToModel(self, cellPath: pathlib.Path,
                       parentItem: libb.libraryItem) -> libb.cellItem:
        cellEntry = libb.cellItem(cellPath)
        parentItem.appendRow(cellEntry)
        return cellEntry

    def addViewToModel(self, viewPath: pathlib.Path,
                       parentItem: libb.cellItem) -> libb.viewItem:
        viewEntry = libb.viewItem(viewPath)
        parentItem.appendRow(viewEntry)
        return viewEntry

    def listLibraries(self) -> List[str]:
        librariesList = []
        for row in range(self.rowCount()):
            itemText = self.item(row, 0).text()
            if itemText:
                librariesList.append(itemText)
        return librariesList

    def listLibraryCells(self, libraryName: str) -> List[str]:
        cellsList = []
        libraryItem = libm.getLibItem(self, libraryName)
        if libraryItem:
            for row in range(libraryItem.rowCount()):
                itemText = libraryItem.child(row, 0).text()
                if itemText:
                    cellsList.append(itemText)
        return cellsList

    def listCellViews(self, libraryName: str, cellName: str, viewTypes: List[str]) -> List[
        str]:
        viewsList = []
        libraryItem = libm.getLibItem(self, libraryName)
        cellItem = libm.getCellItem(libraryItem, cellName)
        if cellItem:
            for row in range(cellItem.rowCount()):
                if cellItem.child(row, 0).viewType in viewTypes:
                    viewsList.append(cellItem.child(row, 0).text())
        return viewsList


class symbolViewsModel(designLibrariesModel):
    """
    Initializes the object with the given `libraryDict` and `symbolViews`.

    Parameters:
        libraryDict (dict): A dictionary containing the library information.
        symbolViews (list): A list of symbol views.

    Returns:
        None
    """

    def __init__(self, libraryDict: dict, symbolViews: list):
        self.symbolViews = symbolViews
        super().__init__(libraryDict)

    def populateLibrary(self, designPath):  # designPath: Path
        """
        Populate library view.
        """
        if designPath.joinpath("reveda.lib").exists():
            libraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                cellItem = self.addCellToModel(designPath.joinpath(cell), libraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json" and any(
                                x in view.name for x in self.symbolViews)]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), cellItem)


class layoutViewsModel(designLibrariesModel):
    def __init__(self, libraryDict: dict, layoutViews: list):
        self.layoutViews = layoutViews
        super().__init__(libraryDict)

    def populateLibrary(self, designPath):  # designPath: Path
        """
        Populate library view.
        """
        if designPath.joinpath("reveda.lib").exists():
            libraryItem = self.addLibraryToModel(designPath)
            cellList = [cell.name for cell in designPath.iterdir() if cell.is_dir()]
            for cell in cellList:
                cellItem = self.addCellToModel(designPath.joinpath(cell), libraryItem)
                viewList = [view.name for view in designPath.joinpath(cell).iterdir() if
                            view.suffix == ".json" and any(
                                x in view.name for x in self.layoutViews)]
                for view in viewList:
                    self.addViewToModel(designPath.joinpath(cell, view), cellItem)


class libraryCheckListView(QListView):
    def __init__(self, parent, model: designLibrariesModel):
        super().__init__(parent)
        self.designLibrariesModel = model
        self.setWindowTitle("Library Check List")
        self.setGeometry(100, 100, 400, 600)
        self.model = QStandardItemModel(self)
        self.setModel(self.model)

        libraries = self.designLibrariesModel.listLibraries()
        for library in libraries:
            item = QStandardItem(library)
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            self.model.appendRow(item)

    def getCheckedLibraries(self):
        checkedLibraries = []
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item.checkState() == Qt.Checked:
                checkedLibraries.append(item.text())
        return checkedLibraries


def updateJSONFieldInLibrary(model: "designLibrariesModel", libraryName: str, key: str,
                             oldValue: str, newValue: str) -> None:
    """
    Update a specific JSON field in all view files within a single library.

    Args:
        model: The designLibrariesModel instance
        libraryName: Name of the library to process
        key: The JSON key to search for
        oldValue: The old value to match
        newValue: The new value to set for the key
    """
    import json
    libItem = libm.getLibItem(model, libraryName)
    if libItem.hasChildren():
        for row in range(libItem.rowCount()):
            cellItem = libItem.child(row)
            if cellItem.hasChildren():
                for row in range(cellItem.rowCount()):
                    viewItem = cellItem.child(row)
                    try:
                        with open(viewItem.viewPath, "r") as f:
                            data = json.load(f)
                            updated = False
                            for item in data:
                                if item.get(key) == oldValue:
                                    updated = True
                                    item[key] = newValue

                        if updated:
                            with open(viewItem.viewPath, "w") as f:
                                json.dump(data, f, indent=4)
                    except Exception as e:
                        print(f"Error updating {viewItem.viewPath}: {str(e)}")


def updateJSONFieldInCell(model: "designLibrariesModel", libraryName: str, cellName: str,
                          key: str, oldValue: str, newValue: str) -> None:
    """
    Update a specific JSON field in all view files within a single cell.

    Args:
        model: The designLibrariesModel instance
        libraryName: Name of the library to process
        cellName: Name of the cell to process
        key: The JSON key to search for
        oldValue: The old value to match
        newValue: The new value to set for the key
    """
    import json
    libItem = libm.getLibItem(model, libraryName)
    cellItem = libm.getCellItem(libItem, cellName)

    if cellItem.hasChildren():
        for row in range(cellItem.rowCount()):
            viewItem = cellItem.child(row)
            try:
                with open(viewItem.viewPath, "r") as f:
                    data = json.load(f)
                    updated = False
                    for item in data:
                        if item.get(key) == oldValue:
                            updated = True
                            item[key] = newValue

                if updated:
                    with open(viewItem.viewPath, "w") as f:
                        json.dump(data, f, indent=4)
            except Exception as e:
                print(f"Error updating {viewItem.viewPath}: {str(e)}")
