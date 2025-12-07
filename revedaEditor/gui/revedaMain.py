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

#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#
import json
import logging
import pathlib
import shutil
from typing import List, Dict

from PySide6.QtCore import (QThreadPool, QThread, Slot, Signal, QTimer, QObject, QSize)
from PySide6.QtGui import (QAction, QIcon, )
from PySide6.QtWidgets import (QGraphicsScene, QApplication, QDialog, QMainWindow, QMessageBox, QVBoxLayout, QWidget,
                               QFileDialog, )
from dotenv import load_dotenv


import revedaEditor.backend.dataDefinitions as ddef
import revedaEditor.backend.libraryMethods as libm
import revedaEditor.fileio.importGDS as igds
import revedaEditor.fileio.importLayp as imlyp
import revedaEditor.fileio.importSpice as impspice
import revedaEditor.fileio.importVeriloga as impvlga
import revedaEditor.fileio.importXschemSym as impxsym
import revedaEditor.gui.fileDialogues as fd
import revedaEditor.gui.helpBrowser as hlp
import revedaEditor.gui.libraryBrowser as libw
import revedaEditor.gui.pythonConsole as pcon
import revedaEditor.gui.revinit as revinit
import revedaEditor.gui.stippleEditor as stip
from revedaEditor.backend.startThread import startThread
from revedaEditor.backend.pdkPaths import importPDKModule
# from revedaEditor.gui.startThread import startThread
from revedaEditor.resources import resources  # noqa: F401

fabproc = importPDKModule('process')


class EventLoopMonitor(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_event_loop)
        self.timer.start(1000)  # Check every second

    def check_event_loop(self):
        print("Event loop is responsive")


class mainwContainer(QWidget):
    """
    Definition for the main app window layout.
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.console = pcon.pythonConsole(globals())
        self.init_UI()

    def init_UI(self):
        # self.console.setfont(QFont("Fira Mono Regular", 12))
        self.console.writeoutput(f"Welcome to Revolution EDA version {revinit.__version__}")
        self.console.writeoutput("Revolution Semiconductor (C) 2025.")
        self.console.writeoutput("Mozilla Public License v2.0 modified with Commons Clause")
        # layout statements, using a grid layout
        gLayout = QVBoxLayout()
        gLayout.setSpacing(10)
        gLayout.addWidget(self.console)
        self.setLayout(gLayout)


class MainWindow(QMainWindow):
    # Class-level constants
    WINDOW_SIZE = QSize(900, 300)
    VIEW_TYPES = {'switch': ["schematic", "veriloga", "spice", "symbol"], 'stop': ["symbol"]}
    PATHS = {'defaultPDK': "defaultPDK", 'testbenches': "testbenches", 'library': "library.json",
        'config': "reveda.conf"}
    STATUS_READY = "Ready"

    # Signal definitions
    sceneSelectionChanged = Signal(QGraphicsScene)
    keyPressedView = Signal(int)

    def __init__(self) -> None:
        """Initialize the main application window."""
        super().__init__()

        # Initialize core components
        self._init_window()
        self._init_data_structures()
        self._init_paths()
        self._init_app_components()
        self.logger_def()

    def _init_window(self) -> None:
        """Initialize window properties and UI components."""
        try:
            # Set window size
            self.resize(self.WINDOW_SIZE)

            # # Position window at bottom of screen
            # screen = QApplication.primaryScreen().availableGeometry()
            # self.move(screen.x(), screen.bottom() - self.height())

            # Create UI elements
            self._createActions()
            self._createMenuBar()
            self._createTriggers()

            # Setup central widget
            self.centralW = mainwContainer(self)
            self.setCentralWidget(self.centralW)

            # Setup status bar
            self.mainW_statusbar = self.statusBar()
            self.mainW_statusbar.showMessage(self.STATUS_READY)
        except Exception as e:
            self._handle_init_error("Window initialization failed", e)

    def _init_data_structures(self) -> None:
        """Initialize data structures and views."""

        self.switchViewList: List[str] = self.VIEW_TYPES['switch']
        self.stopViewList: List[str] = self.VIEW_TYPES['stop']
        self.openViews: Dict = {}

    def _init_paths(self) -> None:
        """Initialize application paths."""

        try:
            self._app = QApplication.instance()
            revedaeditor_pathObj = getattr(self._app, "revedaeditor_pathObj", None)
            if revedaeditor_pathObj is not None:
                self.runPath = revedaeditor_pathObj.parent
            else:
                self.runPath = pathlib.Path.cwd()
            revedaPdkPathObj = getattr(self._app, "revedaPdkPathObj", None)
            if revedaPdkPathObj is not None:
                self.pdkPath = revedaPdkPathObj
            self.outputPrefixPath = self.runPath.parent / self.PATHS['testbenches']
            self.libraryPathObj = self.runPath / self.PATHS['library']
            self.confFilePath = self.runPath / self.PATHS['config']
            revedaPluginPathObj = getattr(self._app, "revedaPluginPathObj", None)
            self.pluginsPath: str = str(revedaPluginPathObj) if revedaPluginPathObj is not None else ""
            # self.pluginsPath: str = str(self._app.revedaPluginPathObj) if hasattr(self._app,
            #     "revedaPluginPathObj") else ""
        except Exception as e:
            self._handle_init_error("Path initialization failed", e)

    def _init_app_components(self) -> None:
        """Initialize application components and resources."""
        try:
            # Core application components
            self.app = QApplication.instance()
            self.logger = logging.getLogger('reveda')
            # Library components
            self.libraryDict = self.readLibDefFile(self.libraryPathObj)
            self.libraryBrowser = libw.libraryBrowser(self)

            # Thread pool setup
            self._setup_thread_pool()

            # Final initialization

            self.loadState()
        except Exception as e:
            self._handle_init_error("Application component initialization failed", e)

    def _setup_thread_pool(self) -> None:
        """Configure and initialize thread pool."""
        self.threadPool = QThreadPool.globalInstance()
        cpuCount = QThread.idealThreadCount()
        self.threadPool.setMaxThreadCount(max(2, cpuCount))
        self.threadPool.setExpiryTimeout(30000)

    def _handle_init_error(self, message: str, error: Exception) -> None:
        """Handle initialization errors."""
        self.logger.error(f"{message}: {str(error)}")

    def logger_def(self):

        c_handler = logging.StreamHandler(stream=self.centralW.console)
        c_handler.setLevel(logging.DEBUG)
        c_format = logging.Formatter("%(levelname)s - %(message)s")
        c_handler.setFormatter(c_format)
        self.logger.addHandler(c_handler)

    def _createMenuBar(self):
        self.mainW_menubar = self.menuBar()
        self.mainW_menubar.setNativeMenuBar(False)
        # Returns QMenu object.
        self.menuFile = self.mainW_menubar.addMenu("&File")
        self.menuTools = self.mainW_menubar.addMenu("&Tools")
        self.importTools = self.menuTools.addMenu("&Import")
        self.menuOptions = self.mainW_menubar.addMenu("&Options")
        self.menuHelp = self.mainW_menubar.addMenu("&Help")
        self.menuFile.addAction(self.exitAction)
        self.menuTools.addAction(self.libraryBrowserAction)
        self.menuTools.addAction(self.createStippleAction)
        self.importTools.addAction(self.importVerilogaAction)
        self.importTools.addAction(self.importSpiceAction)
        self.importTools.addAction(self.importLaypFileAction)
        self.importTools.addAction((self.importXschSymAction))
        self.importTools.addAction(self.importGDSAction)
        self.menuOptions.addAction(self.optionsAction)
        self.menuHelp.addAction(self.helpAction)
        self.menuHelp.addAction(self.aboutAction)
        self.menuOptions.addAction(self.optionsAction)

    def _createActions(self):
        exitIcon = QIcon(":/icons/external.png")
        self.exitAction = QAction(exitIcon, "Exit", self)
        self.exitAction.setShortcut("Ctrl+Q")
        importVerilogaIcon = QIcon(":/icons/document-import.png")
        self.importVerilogaAction = QAction(importVerilogaIcon, "Import Verilog-a file...")
        self.importSpiceAction = QAction(importVerilogaIcon, "Import Spice file...", self)
        self.importLaypFileAction = QAction(importVerilogaIcon, "Import KLayout Layer Prop. " "File...", self)
        self.importXschSymAction = QAction(importVerilogaIcon, "Import Xschem Symbols...", self)
        self.importGDSAction = QAction(importVerilogaIcon, "Import GDS...", self)
        self.importGDSAction.setToolTip("Import GDS to Layout")
        openLibIcon = QIcon(":/icons/database--pencil.png")
        self.libraryBrowserAction = QAction(openLibIcon, "Library Browser", self)
        optionsIcon = QIcon(":/icons/resource-monitor.png")
        self.optionsAction = QAction(optionsIcon, "Options...", self)
        self.createStippleAction = QAction("Create Stipple...", self)
        helpIcon = QIcon(":/icons/document-arrow.png")
        self.helpAction = QAction(helpIcon, "Help...", self)
        self.aboutIcon = QIcon(":/icons/information.png")
        self.aboutAction = QAction(self.aboutIcon, "About", self)

    def _createTriggers(self):
        self.exitAction.triggered.connect(self.exitApp)  # type: ignore
        self.libraryBrowserAction.triggered.connect(self.libraryBrowserClick)
        self.importVerilogaAction.triggered.connect(self.importVerilogaClick)
        self.importSpiceAction.triggered.connect(self.importSpiceClick)
        self.importLaypFileAction.triggered.connect(self.importLaypClick)
        self.importXschSymAction.triggered.connect(self.importXschSymClick)
        self.optionsAction.triggered.connect(self.optionsClick)
        self.importGDSAction.triggered.connect(self.importGDSClick)
        self.createStippleAction.triggered.connect(self.createStippleClick)
        self.helpAction.triggered.connect(self.helpClick)
        self.aboutAction.triggered.connect(self.aboutClick)

    def readLibDefFile(self, libPath: pathlib.Path):
        libraryDict = dict()
        data = dict()
        if libPath.exists():
            with libPath.open(mode="r") as f:
                data = json.load(f)
            if data.get("libdefs") is not None:
                for key, value in data["libdefs"].items():
                    libraryDict[key] = pathlib.Path(value)
            elif data.get("include") is not None:
                for item in data.get("include"):
                    libraryDict.update(self.readLibDefFile(pathlib.Path(item)))
        return libraryDict

    # open library browser window
    def libraryBrowserClick(self):
        self.libraryBrowser.show()
        self.libraryBrowser.raise_()

    def optionsClick(self):
        dlg = fd.appProperties(self)
        load_dotenv()
        import os

        # Set initial values more efficiently using a dictionary
        initial_values = {'rootPathEdit': str(self.runPath), 'simInpPathEdit': str(self.pdkPath),
            'simOutPathEdit': str(self.outputPrefixPath), 'pluginsPathEdit': self.pluginsPath,
            "vaModulePathEdit": os.getenv("REVEDA_VA_MODULE_PATH", str(self.pdkPath)),
            'switchViewsEdit': ", ".join(self.switchViewList), 'stopViewsEdit': ", ".join(self.stopViewList),
            'threadPoolEdit': str(self.threadPool.maxThreadCount())}

        # Set text values in one loop
        for field, value in initial_values.items():
            getattr(dlg, field).setText(value)


        if dlg.exec() == QDialog.Accepted:
            # Get and process all text values at once
            text_values = {'rootPathEdit': dlg.rootPathEdit.text(), 'simInpPathEdit': dlg.simInpPathEdit.text(),
                'simOutPathEdit': dlg.simOutPathEdit.text(), 'pluginsPathEdit': dlg.pluginsPathEdit.text(),
                'vaModulePathEdit': dlg.vaModulePathEdit.text(),
                'switchViewsEdit': dlg.switchViewsEdit.text(), 'stopViewsEdit': dlg.stopViewsEdit.text(),
                'threadPoolEdit': dlg.threadPoolEdit.text()}

            # Update paths
            self.runPath = pathlib.Path(text_values['rootPathEdit'])
            self.pdkPath = pathlib.Path(text_values['simInpPathEdit'])
            self.outputPrefixPath = pathlib.Path(text_values['simOutPathEdit'])
            self.pluginsPath = text_values['pluginsPathEdit']

            self.app.updatePDKPath(self.pdkPath)
            self.app.updatePluginsPath(self.pluginsPath)
            self.app.updateVaModulesPath(text_values['vaModulePathEdit'])

            # Process lists in a more compact way
            self.switchViewList = [x.strip() for x in text_values['switchViewsEdit'].split(',')]
            self.stopViewList = [x.strip() for x in text_values['stopViewsEdit'].split(',')]

            # Update thread pool setting
            try:
                threadCount = int(text_values['threadPoolEdit'])
                self.threadPool.setMaxThreadCount(max(1, threadCount))
            except ValueError:
                pass

            # Save state if needed
            if dlg.optionSaveBox.isChecked():
                self.saveState()

    def importVerilogaClick(self):
        """
        Import a Verilog-A view and add it to a design library.
        """
        impvlga.importVerilogaModule(ddef.viewTuple("", "", ""), "")



    def importSpiceClick(self):
        """
        Import a Spice view and add it to a design library.

        Args:
            self: The instance of the class.

        Returns:
            None
        """
        impspice.importSpiceSubckt(ddef.viewTuple("", "", ""), "")

    def importLaypClick(self):
        importDlg = fd.klayoutLaypImportDialogue(self)
        if importDlg.exec() == QDialog.Accepted:
            lypFile = importDlg.laypFileEdit.text()
            outputFile = importDlg.outputFileEdit.text()
            imlyp.parseLyp(lypFile, outputFile)

    def importXschSymClick(self):
        importDlg = fd.xschemSymIimportDialogue(self, self.libraryBrowser.designView.libraryModel)

        if importDlg.exec() == QDialog.Accepted:
            symbolFiles = importDlg.symFileEdit.text().split(",")
            importLibraryName = importDlg.libNamesCB.currentText()
            scaleFactor = float(importDlg.scaleEdit.text().strip())

            for symbolFile in symbolFiles:
                symbolFileObj = pathlib.Path(symbolFile.strip())
                importObj = impxsym.importXschemSym(self, symbolFileObj, self.libraryBrowser.designView,
                    importLibraryName, )
                importObj.scaleFactor = scaleFactor
                importObj.importSymFile()

    def importGDSClick(self):
        dlg = fd.gdsImportDialogue(self)
        dlg.unitEdit.setText(str(fabproc.gdsUnit))
        dlg.precisionEdit.setText(str(fabproc.gdsPrecision))
        dlg.libNameEdit.setText("importLib")
        if dlg.exec() == QDialog.Accepted:
            gdsImportLibName = dlg.libNameEdit.text().strip()
            gdsImportFileObj = pathlib.Path(dlg.inputFileEdit.text().strip())
            gdsImportLibDirObj = self.libraryDict.get(gdsImportLibName)
            if gdsImportLibDirObj:
                if gdsImportLibDirObj.exists():
                    shutil.rmtree(gdsImportLibDirObj, ignore_errors=True)

                libItem = libm.getLibItem(self.libraryBrowser.designView.libraryModel, gdsImportLibName)
                if libItem:
                    self.libraryBrowser.designView.libraryModel.removeLibraryFromModel(libItem)
                gdsImportLibItem = self.libraryBrowser.designView.libraryModel.addLibraryToModel(gdsImportLibDirObj)
                gdsImportLibDirObj.mkdir(parents=True, exist_ok=True)
                gdsImportLibDirObj.joinpath("reveda.lib").touch(exist_ok=True)
            else:
                gdsImportLibDirObj, gdsImportLibItem = self.createNewLibrary(gdsImportLibName)
            try:
                gdsImportObj = igds.gdsImporter(self, gdsImportFileObj, gdsImportLibItem)
                if gdsImportObj:
                    gdsImportObj.importGDS()
                    self.logger.info("GDS Import completed.")
            except Exception as e:
                self.logger.error(f"GDS Import failed: {e}")

    def createNewLibrary(self, libraryName):
        warning = QMessageBox()
        warning.setIcon(QMessageBox.Warning)
        warning.setWindowTitle("Warning")
        warning.setText("The library does not exist.")
        warning.setInformativeText(f"Do you want to create a new library: {libraryName}?\n"
                                   "Select the parent directory of the library.")
        warning.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        warning.setDefaultButton(QMessageBox.Yes)
        ret = warning.exec()
        if ret == QMessageBox.Yes:

            libDialog = QFileDialog(self, "Select Parent Directory", str(self.runPath))
            libDialog.setFileMode(QFileDialog.Directory)
            if libDialog.exec() == QDialog.Accepted:
                selectedDir = libDialog.selectedFiles()[0]
                libraryPath = pathlib.Path(selectedDir).joinpath(libraryName)
                libraryPath.mkdir(parents=True, exist_ok=True)
                libraryPath.joinpath("reveda.lib").touch(exist_ok=True)
                self.libraryDict[libraryName] = libraryPath
                libraryItem = self.libraryBrowser.designView.libraryModel.addLibraryToModel(libraryPath)
                return libraryPath, libraryItem
        else:
            return None, None

    def createStippleClick(self):
        stippleWindow = stip.stippleEditor(self)
        stippleWindow.show()

    def helpClick(self):
        helpBrowser = hlp.helpBrowser(self)
        helpBrowser.show()

    def aboutClick(self):
        abtDlg = hlp.aboutDialog(self)
        abtDlg.show()

    def loadState(self):
        if not self.confFilePath.exists():
            return

        self.logger.info(f"Configuration file: {self.confFilePath} exists")

        try:
            with self.confFilePath.open(mode="r") as f:
                items = json.load(f)

            if not items:
                return

            # Define default values and paths in a dictionary
            path_settings = {'runPath': ('runPath', self.runPath), 'pdkPath': ('pdkPath', self.pdkPath),
                'outputPrefixPath': ('outputPrefixPath', self.outputPrefixPath)}

            # Update paths
            for attr, (key, default) in path_settings.items():
                setattr(self, attr, pathlib.Path(items.get(key, default)))

            # Handle lists with single operation
            for attr in ['switchViewList', 'stopViewList']:
                value = items.get(attr, [''])
                if value and value[0] != '':
                    setattr(self, attr, value)

            # Restore window geometry
            if 'windowGeometry' in items:
                geom = items['windowGeometry']
                if len(geom) == 4:
                    self.setGeometry(geom[0], geom[1], geom[2], geom[3])

            # Restore thread pool settings
            if 'threadPoolMaxCount' in items:
                self.threadPool.setMaxThreadCount(items['threadPoolMaxCount'])

        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error loading configuration: {e}")

    def saveState(self):
        items = {"runPath": str(self.runPath), "pdkPath": str(self.pdkPath),
            "outputPrefixPath": str(self.outputPrefixPath), "switchViewList": self.switchViewList,
            "stopViewList": self.stopViewList, "windowGeometry": [self.x(), self.y(), self.width(), self.height()],
            "threadPoolMaxCount": self.threadPool.maxThreadCount(), }
        with self.confFilePath.open(mode="w", encoding="utf") as f:
            json.dump(items, f, indent=4)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No, )
        if reply == QMessageBox.Yes:
            if not self.threadPool.waitForDone(5000):
                self.threadPool.clear()
            # for item in self.app.topLevelWidgets():
            self.app.closeAllWindows()
        else:
            event.ignore()

    def exitApp(self):
        self.close()

    # def exitApp(self):
    #     reply = QMessageBox.question(self, "Confirm Exit", "Are you sure you want to exit?",
    #         QMessageBox.Yes | QMessageBox.No, QMessageBox.No, )
    #     if reply == QMessageBox.Yes:
    #         if not self.threadPool.waitForDone(5000):
    #             self.threadPool.clear()
    #         for item in self.app.topLevelWidgets():
    #             item.close()  # self.app.closeAllWindows()

    @Slot()
    def selectionChangedScene(self):
        self.sceneSelectionChanged.emit(self.sender())

    @Slot()
    def viewKeyPressed(self, key: int):
        self.keyPressedView.emit(key)
