# `revedaEditor\gui\revedaMain.py`

**Module:** `revedaEditor.gui.revedaMain`

## Purpose

Module in `revedaEditor\gui`.

## Classes

- `EventLoopMonitor(QObject)`
  - `check_event_loop()`
- `pluginDiscoveryBanner(QFrame)`
- `mainwContainer(QWidget)` — Definition for the main app window layout.
  - `init_UI()`
- `MainWindow(QMainWindow)`
  - `readLibDefFile()`
  - `openProjectClick()`
  - `libraryBrowserClick()`
  - `optionsClick()`
  - `importVerilogaClick()`
  - `importSpiceClick()`
  - `importSpectreClick()`
  - `importVacaskClick()`
  - `importLaypClick()`
  - `importXschSymClick()`
  - `importGDSClick()`
  - `createNewLibrary()`
  - `createStippleClick()`
  - `dismissPluginDiscovery()`
  - `browsePluginsFromBanner()`
  - `setupPluginsClick()`
  - `restartApplication()`
  - `setupPDKsClick()`
  - `setupLibrariesClick()`
  - `helpClick()`
  - `aboutClick()`
  - `licenseClick()`
  - `loadAppState()`
  - `saveAppState()`
  - `closeEvent()`
  - `exitApp()`
  - `selectionChangedScene()`
  - `viewKeyPressed()`
  - internals: `_init_window()`, `_initDataStructures()`, `_initPaths()`, `_initAppComponents()`, `_setupThreadPool()`, `_handleInitError()`, `_loggerDef()`, `_createMenuBar()`, `_createActions()`, `_createTriggers()`, `_updateRecentProjectsMenu()`, `_openRecentProject()` … (+6)

## Depends on

- [[revedaEditor\backend\bindkeys|revedaEditor.backend.bindkeys]]
- [[revedaEditor\backend\dataDefinitions|revedaEditor.backend.dataDefinitions]]
- [[revedaEditor\backend\libraryMethods|revedaEditor.backend.libraryMethods]]
- [[revedaEditor\backend\projectManager|revedaEditor.backend.projectManager]]
- [[revedaEditor\fileio\importGDS|revedaEditor.fileio.importGDS]]
- [[revedaEditor\fileio\importLayp|revedaEditor.fileio.importLayp]]
- [[revedaEditor\fileio\importSpectre|revedaEditor.fileio.importSpectre]]
- [[revedaEditor\fileio\importSpice|revedaEditor.fileio.importSpice]]
- [[revedaEditor\fileio\importVacask|revedaEditor.fileio.importVacask]]
- [[revedaEditor\fileio\importVeriloga|revedaEditor.fileio.importVeriloga]]
- [[revedaEditor\fileio\importXschemSym|revedaEditor.fileio.importXschemSym]]
- [[revedaEditor\gui\fileDialogues|revedaEditor.gui.fileDialogues]]
- [[revedaEditor\gui\helpBrowser|revedaEditor.gui.helpBrowser]]
- [[revedaEditor\gui\libraryBrowser|revedaEditor.gui.libraryBrowser]]
- [[revedaEditor\gui\pythonConsole|revedaEditor.gui.pythonConsole]]
- [[revedaEditor\gui\revinit|revedaEditor.gui.revinit]]
- [[revedaEditor\gui\stippleEditor|revedaEditor.gui.stippleEditor]]

## Used by

- [[reveda|reveda]]
- [[revedaEditor\tests\test_platform_hardening|revedaEditor.tests.test_platform_hardening]]
- [[revedaEditor\tests\test_plugin_discovery|revedaEditor.tests.test_plugin_discovery]]
