# `revedaEditor/gui`

Windows, dialogs and editor chrome (QMainWindow/QDialog layer).

## Modules

- [[revedaEditor/gui/__init__|__init__.py]] — Package marker for windows, dialogs and editor chrome
- [[revedaEditor/gui/alignItems|alignItems.py]] — Align-items dialog plus the edge/line alignment geometry helpers it invokes
- [[revedaEditor/gui/configEditor|configEditor.py]] — Hierarchy config-view editor: `configEditor` window + container driving switch/stop view traversal
- [[revedaEditor/gui/editFunctions|editFunctions.py]] — Shared small widgets (`shortLineEdit`, `boldLabel`, `longLineEdit`) used across dialogs
- [[revedaEditor/gui/editorFactory|editorFactory.py]] — `EditorFactory.createEditor`
- [[revedaEditor/gui/editorTypes|editorTypes.py]] — `Protocol` definitions typing the editor-window/container contract (`EditorContainer`, `BaseEditor`)
- [[revedaEditor/gui/editorViews|editorViews.py]] — `editorView` (QGraphicsView): zoom/pan, `viewRect` tracking, grid/line background rendering, mouse/key event forwarding to the scene
- [[revedaEditor/gui/editorWindow|editorWindow.py]] — `editorWindow` — QMainWindow base class for all editors: menus/toolbars/actions, hardcoded+bindkey shortcuts, cellview lock acquisition,…
- [[revedaEditor/gui/fileDialogues|fileDialogues.py]] — Cell/view/library dialogs: create/delete/rename/copy/select-cellview dialogs and the library dialogs
- [[revedaEditor/gui/findDialogue|findDialogue.py]] — Non-modal find/replace dialog and the check-marker browser for the schematic editor
- [[revedaEditor/gui/helpBrowser|helpBrowser.py]] — Markdown documentation browser plus about/license dialogs
- [[revedaEditor/gui/layoutDialogues|layoutDialogues.py]] — Layout creation/property dialogs: instance placement (incl. arrays), paths, pins, labels, vias, multipart parameters, layer ops
- [[revedaEditor/gui/layoutEditor|layoutEditor.py]] — `layoutEditor` window + `layoutContainer`: layout menus/actions (incl. Group/Ungroup Items), save/load, GDS export, SDL sync, flyline and cross-probe actions
- [[revedaEditor/gui/libraryBrowser|libraryBrowser.py]] — `libraryBrowser` — the design-libraries window hosting the column/tree view, context menus, and new/open cellview entry points
- [[revedaEditor/gui/libraryRegistry|libraryRegistry.py]] — Library registry window for managing configured libraries
- [[revedaEditor/gui/lsw|lsw.py]] — Layer Selection Window (LSW): layer table model/view, object-filter table, stipple delegate
- [[revedaEditor/gui/lvsResults|lvsResults.py]] — LVS results dialog presenting the imported LVS database
- [[revedaEditor/gui/pdkRegistry|pdkRegistry.py]] — PDK registry window for managing configured PDKs
- [[revedaEditor/gui/pluginsRegistry|pluginsRegistry.py]] — Plugin registry window with background download thread
- [[revedaEditor/gui/propertyDialogues|propertyDialogues.py]] — Schematic/symbol property and creation dialogs (instance placement, pins, labels, parameter widgets)
- [[revedaEditor/gui/pythonConsole|pythonConsole.py]] — Interactive Python console widget embedded in the main window (stdin/stdout redirection, history)
- [[revedaEditor/gui/revedaMain|revedaMain.py]] — `MainWindow` — application shell: menus, library-browser host, `openViews` registry, `reveda.conf` app state + session persistence, bindkey…
- [[revedaEditor/gui/revinit|revinit.py]] — Version constant (`__version__`)
- [[revedaEditor/gui/schematicEditor|schematicEditor.py]] — `schematicEditor` window + `schematicContainer`: schematic menus/actions, load/save flows, config-view creation
- [[revedaEditor/gui/stippleEditor|stippleEditor.py]] — Stipple-pattern editor for LSW fill textures
- [[revedaEditor/gui/symbolEditor|symbolEditor.py]] — `symbolEditor` window + `symbolContainer`: symbol drawing actions, label/attribute dialogs
- [[revedaEditor/gui/textEditor|textEditor.py]] — Text-editor family (JSON/Verilog-A/SPICE/Spectre/VACASK/Xyce) with per-language syntax highlighters
- [[revedaEditor/gui/toolsDialogues|toolsDialogues.py]] — `findProjectEditors` dialog for locating open editor windows
- [[revedaEditor/gui/utilDialogues|utilDialogues.py]] — Customized print dialog (`revedaPrintDialog`)
