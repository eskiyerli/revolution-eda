# Revolution EDA Main Window

The main window is the starting point for Revolution EDA. It gives you access to the Library
Browser, import tools, plugin and PDK setup, application options, and an integrated Python
console area that shows startup messages and logging output.

<!-- Screenshot placeholder: main window -->
<img src="assets/revedaMainWindow.png" alt="Revolution EDA main window" class="image fit">

## Quick Orientation

- The main window is intentionally simple: most editing happens in the schematic, symbol,
  layout, and config editors opened from the Library Browser.
- The central area includes an integrated **Python console** that displays the welcome
  banner (`Welcome to Revolution EDA version 0.9.0`) and all application log messages.
- The menu bar is focused on application setup rather than geometry editing.
- The **Tools** menu is where you will spend most of your time when setting up a working
  environment.

## Application Startup (`reveda.py`)

`reveda.py` is the single entrypoint for the entire application. It creates the custom
`revedaApp` (a `QApplication` subclass), resolves paths, and opens the main window.

### Startup Sequence

1. **Parse command-line arguments** — supports `--project <path>` (open a specific project
   directory) and `--switching` (internal flag used during project restarts to show a splash
   screen).
2. **Create `revedaApp`** — the application class resolves the project directory, shows a
   splash screen, and loads environment variables.
3. **Project directory resolution** — priority order:
   - Explicit `--project` argument
   - Current working directory (if writable)
   - `~/reveda_projects/` as a fallback (user is prompted to confirm/create)
4. **Environment variable loading** — `.env` files are loaded with the following priority:
   - Project-specific `.env` (in the project directory)
   - User-level `.env` (in `~/.reveda/`)
   - Bundled `.env.example` (in the install directory)
5. **Central directory setup** — `~/.reveda/` is created if needed. It holds the compiled
   license module, a shared plugins directory, and user-level settings.
6. **PDK path resolution** — `REVEDA_PDK_PATH` from environment; falls back to the bundled
   `defaultPDK/`. Relative paths are resolved against the project directory first, then the
   install directory.
7. **Plugin path resolution** — `REVEDA_PLUGIN_PATH` from environment; falls back to
   `~/.reveda/plugins/`.
8. **License path setup** — `~/.reveda/` is appended to `sys.path` so that the compiled
   `revedaLicense` module is discoverable. In development mode, the source-relative
   `revedaLicense/` directory takes priority.
9. **`MainWindow` creation** — the main window initializes menus, actions, the library
   browser, thread pool, and the embedded Python console.
10. **`ProjectManager.open_project()`** — loads the project's `.env`, PDK, plugins,
    `library.json`, and `reveda.conf` for the target directory.
11. **Show main window and dismiss splash** — once the window is visible the splash is
    removed and the Qt event loop begins.

### Command-Line Usage

```bash
# Open a specific project directory
reveda --project /path/to/my/project

# Or simply run from the project directory
cd /path/to/my/project
reveda
```

### Nuitka Standalone Packaging

`reveda.py` contains embedded Nuitka directives (comment block near the top) that configure
standalone builds for Windows, Linux, and macOS. Key points:

- Output lands in platform-specific directories (e.g. `C:\Users\eskiye50\dist` on Windows).
- Plugins, PDKs, and the license module are deliberately excluded from the binary
  (`--nofollow-import-to`) so they can be loaded at runtime from user-configurable paths.
- Product metadata (name, version, copyright, icon) is set via Nuitka project comments.

### Application Restart for Project Switching

When the user switches projects (`File -> Open Project...` or a recent project entry), the
application performs a clean restart:

1. Current state is saved to `reveda.conf`.
2. The target project path is stored in `REVEDA_RESTART_PROJECT`.
3. The app exits with exit code `99` (`RESTART_EXIT_CODE`).
4. `main()` detects the restart code and spawns a new process with `--project <new_path>
   --switching`.
5. The restart logic handles AppImage, Nuitka standalone binaries, and source-mode runs
   transparently.

## Typical Workflow

1. Launch Revolution EDA from the project directory, or use `--project <path>`.
2. The application loads `.env`, library definitions, and saved state from the project.
3. Open the **Library Browser** from `Tools -> Library Browser`.
4. Create or open a library.
5. Create a cell and then create or open a cellview such as `schematic`, `symbol`, or
   `layout`.
6. If needed, configure PDKs, plugins, and library registries from the main window menus.
7. To switch to a different project, use `File -> Open Project...` or `File -> Recent
   Projects` — the application will restart cleanly with the new configuration.

## Menu Actions You Will Use Most

### File Menu

The main window File menu manages project-level operations and application lifecycle.

- `File -> Open Project...`: Opens a project directory and restarts the application to load
  the new project's configuration cleanly.
- `File -> Recent Projects`: Lists the most recently opened project directories (up to 5).
  Selecting an entry restarts the application pointing at that project.
- `File -> Exit`: Closes the application (prompts for confirmation).

| Action | Shortcut | Notes |
| --- | --- | --- |
| `File -> Open Project...` | `Ctrl+Shift+O` | Opens a project directory (triggers restart). |
| `File -> Recent Projects` | — | Quick access to previously opened projects. |
| `File -> Exit` | `Ctrl+Q` | Closes Revolution EDA (after confirmation). |

#### Project Management

Revolution EDA uses a **project directory** concept. A project directory contains:

- `.env` — environment variables (PDK path, plugin path, VA module path)
- `library.json` — library definitions for the project
- `reveda.conf` — saved application state (window geometry, view lists, thread pool settings)

**How project loading works (via `ProjectManager`):**

1. On startup, the `revedaApp` resolves the project directory from the `--project` argument,
   the current working directory, or the default `~/reveda_projects/`.
2. `ProjectManager.open_project()` is called with the resolved directory. It:
   - Validates the directory exists and is readable.
   - Saves the current project state (if switching from another project).
   - Loads `.env` (copies `.env.example` from the install directory if missing), clearing
     stale environment variables to prevent leakage between projects.
   - Resolves and applies PDK and plugin paths.
   - Loads `library.json` (supports both `libdefs` and `include` formats).
   - Loads and applies `reveda.conf` (window geometry, view lists, thread pool count).
   - Updates the recent projects store and window title.

**Switching projects:**

When you select a different project directory via `File -> Open Project...` or the
`Recent Projects` menu, `ProjectManager.switch_project()`:

1. Saves the current project state to `reveda.conf`.
2. Records the target in the recent projects store.
3. Sets `REVEDA_RESTART_PROJECT` and exits with code `99`.
4. `main()` relaunches the process with `--project <target> --switching`.

This guarantees that PDKs, plugins, and all imported modules are loaded cleanly without
stale state from the previous project.

**Recent projects** are persisted in `~/.reveda/reveda_settings.ini` (via `QSettings`)
and survive application restarts. Up to 5 entries are stored, most recent first.

**Non-existent project directory:** If the resolved project directory does not exist on
startup, the application shows a dialog with three choices: Create it, Browse for another
directory, or Cancel (exit).

### Tools Menu

The Tools menu is the main control center of the application.

Most actions in this menu open a dedicated window or dialog rather than directly modifying
the current design. In practice, `Tools` is where you configure application resources,
import external design data, and launch utility editors that support the main schematic,
symbol, and layout workflows.

<img src="assets/revedaToolsMenu.png" alt="Revolution EDA Tools menu">

It includes the following menu items:

- `Library Browser`
- `Import`
- `Plugins`
- `Libraries`
- `PDKs`
- `Create Stipple...`

#### Library Browser

The Library Browser is the main user workspace for opening and organizing design data.

<img src="assets/libraryBrowser.png" alt="Revolution EDA Library Browser">

From the Library Browser, users typically:

- create or open libraries
- create, rename, copy, or delete cells
- create, open, copy, rename, or delete cellviews

It is also the normal entry point into the actual editors. Once a library and cell exist,
you usually open a cellview from here and continue your work in the schematic, symbol,
layout, or config window associated with that view.

In day-to-day use, think of the Library Browser as the design-data manager for the whole
project: it shows the available libraries, their cells, and the set of cellviews stored in
each cell.

Implemented cellview types include but are not limited to:

| Cellview | Tool |
| --- | --- |
| `schematic` | Schematic Editor |
| `symbol` | Symbol Editor |
| `layout` | Layout Editor |
| `config` | Config Editor |
| `veriloga` | Text editor / linked Verilog-A flow |
| `spice` | Text editor / linked SPICE flow |
| `pcell` | Text editor / PCell reference flow |
| `revbench` | Simulation environment (when available) |

#### Import Submenu

The Import submenu is used to bring design data in various formats into Revolution EDA.

![importMenus.png](assets/importMenus.png)

Available import actions include:

- `Import Verilog-a file...`
- `Import Spice file...`
- `Import KLayout Layer Prop. File...`
- `Import Xschem Symbols...`
- `Import GDS...`

These actions are used to build libraries, symbols, and layouts from external sources.

The import tools serve different purposes:

- `Import Verilog-a file...`: imports a Verilog-A module into a library/cell as a Verilog-A
  view. This flow is useful when you already have behavioral model source and want to add it
  to a design library. The import dialog can also create a symbol for the module.

![verilogaimport.png](assets/verilogaimport.png)

If `Create a new Symbol` checkbox is checked, a new symbol for the Verilog-A module will be
generated. You will be able to determine the pin locations and stub size in the symbol
editor after import.

![createImportSymbolDialogue.png](assets/createImportSymbolDialogue.png)

Generated symbol will have the correct attributes set for successful netlisting and
simulation with Xyce simulator.

![importedVerilogaSymbolAttributes.png](assets/importedVerilogaSymbolAttributes.png)

- `Import Spice file...`: imports a SPICE subcircuit into a selected library/cell as a SPICE
  view. Like the Verilog-A flow, this is a convenient way to seed a design library from an
  existing netlist and optionally create a matching symbol.

![importSpice.png](assets/importSpice.png)

If `Create a new Symbol` checkbox is checked, a new symbol for the SPICE subcircuit will be
generated:

![importedSpiceSubcktSymbol.png](assets/importedSpiceSubcktSymbol.png)

Symbol for imported SPICE file will have symbol attributes generated for successful
netlisting with SPICE-like simulators.

![importedSpiceSymbolAttributes.png](assets/importedSpiceSymbolAttributes.png)

- `Import KLayout Layer Prop. File...`: converts a KLayout `.lyp` layer-properties file into
  Revolution EDA layer-definition output. This is mainly a technology-setup helper when you
  want to reuse an existing KLayout layer/color description as a starting point.
- `Import Xschem Symbols...`: imports one or more Xschem `.sym` symbol files into a selected
  library. The dialog lets you choose the destination library and a scale factor, so this
  tool is especially useful when migrating symbol sets from an Xschem-based flow.
- `Import GDS...`: imports geometry from a GDS file into a dedicated Revolution EDA library.
  The dialog asks for a target library name plus GDS unit and precision values, making it a
  practical bridge from external layout data into native layout cellviews.

Practical notes:

- Use imports as starting points, not as a guarantee of perfect one-to-one translation.
- For symbol and layout imports, it is often worth opening the generated result afterward to
  check scaling, layers, labels, and hierarchy.
- The GDS import dialog defaults the target library name to `importLib`, which is useful for
  keeping imported layout data separate from other design libraries.

#### Plugins Submenu

`Tools -> Plugins -> Setup Plugins...` opens plugin management for installed or available
plugins.

The plugin registry window shows available plugins, whether each one is already installed,
and basic metadata such as type, version, and license. It will check the
`REVEDA_PLUGIN_PATH` environment variable if it is already set or `Plugins Path` from
Options Dialogue if it is set there separately.

![pluginsRegistry.png](assets/pluginsRegistry.png)

From `Revolution EDA Plugin Registry` dialogue, you can:

- refresh the registry listing
- inspect plugin descriptions
- download and install a plugin
- uninstall an installed plugin

In normal use, this is the preferred way to add optional capabilities such as simulation,
plotting, or AI-assisted tools. After installing or uninstalling plugins, restarting the
application is the safest way to ensure menu integrations are reloaded cleanly.

For more detail, see [Plugins](./plugins.md).

#### Libraries Submenu

`Tools -> Libraries -> Setup Libraries` opens the library registry and installation tools.

![libraryRegistry.png](assets/libraryRegistry.png)

This window is used to browse downloadable design libraries and install them into a chosen
installation prefix. It shows whether a listed library is already installed, provides a
description panel, and supports refresh, install, and uninstall operations.

Unlike the Library Browser, which manages the libraries already visible in your working
environment, the library registry is focused on acquiring library content. When a library is
installed from this window, Revolution EDA also updates the active library definitions so the
new library becomes available in the Library Browser.

#### PDKs Submenu

`Tools -> PDKs -> Setup PDK...` opens the PDK management flow.

![pdkRegistry.png](assets/pdkRegistry.png)

The PDK registry window lets you browse available PDK packages, view process and version
information, choose the local PDK storage directory, and install or uninstall PDKs. The list
also indicates whether an entry is source or binary and can show when an installed PDK has a
newer version available.

This tool is mainly about obtaining and maintaining local PDK packages. Selecting which PDK
the application actively uses is still handled through application configuration such as the
Options dialog or environment variables like `REVEDA_PDK_PATH`.

#### Create Stipple

`Tools -> Create Stipple...` opens the stipple editor used for layout fill-pattern design.

This is a small utility editor for creating or adjusting stipple patterns used in layout
display and related layer-visualization workflows. You typically use it when defining custom
fill appearances rather than while editing device geometry directly.

<img src="assets/stippleEditor.png" alt="Revolution EDA stipple editor" class="image fit">

### Options Menu

`Options -> Options...` opens the main application settings dialog.

This is where you configure application-level paths and defaults such as:

- run/root path
- PDK path
- simulation output path
- plugins path
- Verilog-A module path
- switch view list
- stop view list
- thread-pool size

Important environment-related paths may also be provided through environment variables such
as:

- `REVEDA_PDK_PATH`
- `REVEDA_PLUGIN_PATH`
- `REVEDA_VA_MODULE_PATH`

Changes made in the Options dialog can be persisted to `reveda.conf` by checking the save
checkbox. Additionally, when PDK, plugin, or VA module paths are updated, they are
automatically written back to the project's `.env` file.

<img src="assets/optionsDialogue.png" alt="Revolution EDA options dialog" class="image fit">

### Help Menu

The Help menu contains:

- `Help...` — opens the integrated help browser
- `License...` — shows license information dialog
- `About` — displays application version and copyright

## Main Window Concepts

### Integrated Python Console

The main window embeds a Python console widget that shows the welcome banner and logging
output. On startup it displays:

```
Welcome to Revolution EDA version 0.9.0
Revolution Semiconductor (C) 2026.
Mozilla Public License v2.0
```

Application log messages (INFO, WARNING, ERROR, DEBUG) are streamed to this console via a
custom logging handler, making it useful for diagnostics, observing import results, and
monitoring background operations.

### Thread Pool and Background Work

Revolution EDA uses the global `QThreadPool` for background work. The thread count defaults
to the system's ideal thread count (minimum 2) with a 30-second idle thread expiry. The
count is configurable via the Options dialog and persisted in `reveda.conf`.

### Plugin and PDK Integration

Plugins and PDKs can extend application behavior, menus, and downstream flows. Their setup
is managed from the main window rather than from the individual drawing editors.

- **Plugins** are loaded from `REVEDA_PLUGIN_PATH` or `~/.reveda/plugins/`. The
  `pluginsLoader` scans that directory, imports packages, and reads each plugin's
  `config.json` for menu wiring.
- **PDK** is loaded from `REVEDA_PDK_PATH` or the bundled `defaultPDK/`. The `pdkConfig`
  helper reads the PDK's `config.json` for additional menu actions (e.g., DRC integration).

### Splash Screen

A splash screen is shown during startup and project switching. It displays the Revolution
EDA logo and a loading message indicating which project is being opened. The splash is
dismissed once the main window becomes visible.

### Close Behavior

When closing the application normally (via `File -> Exit` or the window close button), a
confirmation dialog is shown. If the user confirms:

1. `ProjectManager.save_current_state()` writes current settings to `reveda.conf`.
2. The thread pool is given 5 seconds to finish pending work before being cleared.
3. All tracked editor/plugin windows are explicitly closed.
4. The application exits.

During a project-switch restart, the confirmation dialog is suppressed — the close proceeds
immediately.

## Final Notes

- Think of the main window as the **launch and configuration hub** for the application.
- Think of the Library Browser as the **entry point to actual design data**.
- Once your libraries and PDK are configured, most day-to-day design work moves into the
  editor windows rather than the main window itself.

For the next step in a typical workflow, continue with:

- [Installation](./installation.md)
- [Schematic Editor Tutorial](./schematicTutorial.md)
- [Symbol Editor Tutorial](./symbolTutorial.md)
- [Layout Editor Tutorial](./layoutTutorial.md)
