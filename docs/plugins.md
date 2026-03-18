# Revolution EDA Plugins

This guide explains what plugins are in Revolution EDA, how users install and use them, how developers create them, how `config.json` works, and how plugins are published to the Revolution EDA plugin registry.

## Quick Orientation

- Plugins extend Revolution EDA without changing the core application.
- End users typically encounter plugins as extra menu items, new editor actions, or support for
  additional view flows.
- Most users install plugins through `Tools -> Plugins -> Setup Plugins...`.
- Developers package plugins as Python packages with a `config.json` file and callable
  callback functions.

## What Plugins Are

Plugins are add-ons that extend Revolution EDA without modifying the core application. Typical plugin categories are:

- Simulation workflows
- Result plotting tools
- AI-assisted design tools
- Custom view handlers and editor menu actions

In daily use, plugins usually appear as additional menu actions in editors or as handlers for specific view types.

## How Plugins Are Loaded

At startup, Revolution EDA loads plugins from the directory configured by `REVEDA_PLUGIN_PATH`.

- The loader scans that directory with `pkgutil.iter_modules()`.
- Each discovered package is imported.
- The app logs discovery/load status in `reveda.log`.
- The plugin's `config.json` is read to add menu actions.

Important:
- If `REVEDA_PLUGIN_PATH` is not set, plugins are not loaded by `reveda.py`.
- Use `Tools -> Plugins -> Setup Plugins...` and application setup paths to configure plugin location.

## Plugin Folder Structure

Each plugin should be a Python package under the plugin directory:

```text
<plugins_path>/
  myPlugin/
    __init__.py
    config.json
    <implementation>.py
    README.md            (recommended)
```

Minimum required files:
- `__init__.py` so Python can import the package
- `config.json` for metadata and menu definitions

## Using Plugins (End Users)

Most users only need three steps:

1. Open the plugin registry UI from `Tools -> Plugins -> Setup Plugins...`.
2. Install the plugin you want.
3. Restart Revolution EDA.

### Install from Plugin Registry UI

1. Open Plugins Registry Dialogue: `Tools -> Plugins -> Setup Plugins...`.
2. The Plugin Registry window downloads plugin metadata from:
   `https://raw.githubusercontent.com/eskiyerli/revolutionEDA_plugins/main/plugins.json`

<img src="assets/pluginsRegistry.png" alt="Plugins registry window" class="image fit" /> 

2. Select a plugin and click `Download / Install`.
3. Restart Revolution EDA after installation.

Notes:
- `source` plugins use a single `url` field in the registry.
- `binary` plugins can provide `binary_urls`; the app chooses the best URL for your OS, CPU, and Python version.

### Uninstall

1. Open `Tools -> Plugins -> Setup Plugins...`.
2. Select an installed plugin.
3. Click `Uninstall`.
4. Restart Revolution EDA.

### Manual Install

1. Copy plugin folder into your configured plugins directory (`REVEDA_PLUGIN_PATH`).
2. Ensure plugin contains `__init__.py` and `config.json`.
3. Restart the app.

## `config.json` Explained

The plugin loader reads each plugin's `config.json` and uses `menu_items` to inject menu actions.

### What `config.json` Actually Does At Runtime

In the current implementation, `config.json` is used for menu/action registration, not for plugin import.

- Plugin import/discovery is done by folder/package name via `pkgutil.iter_modules()`.
- After import, the loader reads `<plugin>/config.json`.
- The loader iterates `menu_items` and creates UI actions.
- For each action, it resolves `callback` with `getattr(plugin_module, callback_name)` and connects it.
- If callback is missing, that menu item is skipped.

What is effectively required in `config.json` for behavior:
- `menu_items` list
- For each item: `location`, `menu`, `action`, `callback`

What is metadata only (useful to users/maintainers, but not used by menu wiring logic):
- `plugin_name`, `plugin_version`, `description`, `license`, `author`, `copyright`

Example:

```json
{
  "plugin_name": "myPlugin",
  "plugin_version": "0.1.0",
  "description": "Example plugin",
  "license": "Mozilla Public License 2.0",
  "author": "Your Name or Company",
  "menu_items": [
    {
      "location": "menuBar",
      "menu": "Tools",
      "action": "My Action",
      "text": "Run My Action",
      "callback": "runMyAction",
      "shortcut": "Ctrl+M",
      "checked": 0,
      "apply": ["schematicEditor", "symbolEditor", "layoutEditor"]
    }
  ]
}
```

Key fields in `menu_items`:
- `menu`: existing menu name where action is added (for example `Tools`, `Simulation`, `Results`)
- `callback`: function name in plugin module (`__init__.py` imported symbols)
- `apply`: list of window class names where action is visible
- Optional: `text`, `icon`, `shortcut`, `checked`

### Real Examples

`aiTerminal` example:
- `plugins/aiTerminal/config.json` defines one menu item in `Tools`.
- `callback` is `toggleAITerminal`.
- `plugins/aiTerminal/__init__.py` exposes `toggleAITerminal`.
- `plugins/aiTerminal/aiTerminal.py` implements `def toggleAITerminal(editorWindow): ...`.

`revedasim` example:
- `plugins/revedasim/config.json` defines `Simulation Environment...` under `Simulation` menu for `schematicEditor`.
- `callback` is `startRevedasim`.
- `plugins/revedasim/__init__.py` exposes `startRevedasim`.
- `plugins/revedasim/simMainWindow.py` implements `def startRevedasim(schematicEditor): ...`.

Important distinction:
- `config.json` does not define view-type dispatch.
- View dispatch uses plugin module attributes/functions such as `viewTypes`, `createCellView`, and `openCellView` (as used by `revedasim`).

Practical rules:
- Keep plugin folder name and importable package name consistent.
- Ensure callback functions are exposed and importable.
- Keep import side effects minimal to avoid startup failures.

## Creating a Plugin

1. Create a package directory under your plugins path.
2. Add `__init__.py` with callable functions used by menu callbacks.
3. Add `config.json` with metadata and `menu_items`.
4. Test by restarting Revolution EDA and checking `reveda.log`.
5. If needed, add support for view opening by exposing `viewTypes` plus `createCellView` and/or `openCellView` in the plugin module.

Minimal `__init__.py` example:

```python
def runMyAction(editor_window):
    editor_window.logger.info("My plugin action executed")
```

## Plugin Registry (`plugins.json`) Format

The online plugin catalog is a JSON file with a top-level `plugins` list.

Example:

```json
{
  "plugins": [
    {
      "name": "aiTerminal",
      "version": "0.1.0",
      "license": "Mozilla Public License 2.0",
      "type": "source",
      "description": "AI assistant terminal plugin",
      "url": "https://raw.githubusercontent.com/eskiyerli/revolutionEDA_plugins/main/aiTerminal/aiTerminal.zip"
    },
    {
      "name": "revedasim",
      "version": "0.8.8",
      "license": "Proprietary",
      "type": "binary",
      "description": "Simulation plugin",
      "binary_urls": {
        "linux-x86_64-py313": "https://raw.githubusercontent.com/eskiyerli/revolutionEDA_plugins/main/revedasim/linux-x86_64-py313.zip"
      }
    }
  ]
}
```

For binary plugins, key matching priority is:

1. `{os}-{arch}-py{major}{minor}`
2. `{os}-{arch}`
3. `{os}`
4. fallback `url`

Where values come from Python runtime information used by the app.

## How To Upload a Plugin to the Revolution EDA Plugin Repository

Current workflow is repository-based (not an in-app upload button):

1. Package your plugin as a ZIP that extracts into a plugin folder (for example `myPlugin/`).
2. Clone `revolutionEDA_plugins` repository. 
   `https://github.com/eskiyerli/revolutionEDA_plugins`
3. Add your zip file(s) to repo directory.
4. Add or update an entry in that repository's `plugins.json`.
5. For binary plugins, provide `binary_urls` entries for supported platform/Python combinations.
6. Open a pull request.
7. Include plugin name and version in the pull request description.
8. Include license in the pull request description. Plugins in Revolution EDA can have their own license terms, independent of Revolution EDA licensing, including charging fees for licenses.
9. Include a short description in the pull request description.
10. Include source/binary ZIP URLs in the pull request description.
11. Include tested platforms in the pull request description.
12. After merge, users can install from `Tools -> Plugins -> Setup Plugins...`.

Recommended release checklist:
- Bump plugin version in your plugin and registry entry
- Verify ZIP layout and callback imports
- Test clean install from registry URL
- Confirm menu actions appear in target editors

## Troubleshooting

Plugin not shown:
- Verify `REVEDA_PLUGIN_PATH` points to the correct folder.
- Verify plugin folder contains `__init__.py` and valid `config.json`.
- Restart app after install/uninstall.

Plugin found but action missing:
- Check `menu` name matches an existing menu in target window.
- Check `apply` includes the actual editor class name.
- Check callback function exists in the plugin module.

Import/load failure:
- Inspect `reveda.log` for `Failed to load plugin ...` errors.
- Install missing Python dependencies in the same environment used by Revolution EDA.

## Related Files

- `reveda.py`
- `revedaEditor/backend/pluginsLoader.py`
- `revedaEditor/gui/pluginsRegistry.py`
- `plugins.json`
- [Binary Plugins](./binaryPlugins.md) document.

  
