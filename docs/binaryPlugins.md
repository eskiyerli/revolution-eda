# Binary Plugins for Revolution EDA

This document focuses on the fine points of creating and publishing binary plugins.
For general plugin concepts (what plugins are, basic install/use, and generic `config.json` behavior), see `docs/plugins.md`.

## What Makes a Plugin "Binary"

A binary plugin contains compiled artifacts (for example `.pyd`, `.so`, platform-specific executables, or Nuitka-produced modules).
Because binaries are OS/architecture/Python-version sensitive, you usually publish more than one package.

## Runtime Selection Logic Used by Plugin Registry

When a plugin entry has `type: "binary"`, Revolution EDA selects download URL with this priority:

1. `{os}-{arch}-py{major}{minor}`
2. `{os}-{arch}`
3. `{os}`
4. fallback `url`

Values are generated from runtime info:
- `os = platform.system().lower()`
- `arch = platform.machine().lower()`
- `py = py{major}{minor}` from `sys.version_info`

Example keys:
- `linux-x86_64-py313`
- `windows-amd64-py314`
- `darwin-arm64-py313`

## Critical Packaging Rule: Use ZIP Archives

The current Plugin Registry installer treats `.zip` as an archive and extracts it.
Non-zip URLs are downloaded as a single file and written into a plugin subfolder, which is usually not what a binary plugin needs.

Recommended:
- Publish ZIP files for both `url` and `binary_urls` values.
- Ensure ZIP extracts to a single top-level plugin directory.

Correct ZIP structure:

```text
myPlugin-linux-x86_64-py314.zip
  myPlugin/
    __init__.py
    config.json
    my_binary_module.cp314-win_amd64.pyd   # or .so/.dll/etc.
    ...
```

Avoid:
- ZIP without top-level plugin folder
- TAR/TGZ URLs in registry for plugin installs

## `config.json` in Binary Plugins

`config.json` has the same runtime role for binary and source plugins:
- It is read after plugin import.
- `menu_items` are used to create menu actions.
- `callback` names must resolve to attributes on the imported plugin module.

Important:
- Binary-specific delivery is handled by registry `plugins.json` (`type`, `url`, `binary_urls`).
- Plugin-local `config.json` does not select platform binaries.

Minimal binary plugin `config.json`:

```json
{
  "plugin_name": "myPlugin",
  "plugin_version": "1.2.0",
  "description": "Binary plugin example",
  "license": "Proprietary",
  "author": "Your Company",
  "menu_items": [
    {
      "location": "menuBar",
      "menu": "Tools",
      "action": "Run My Binary Tool",
      "callback": "runTool",
      "apply": ["schematicEditor"]
    }
  ]
}
```

## Registry Entry for Binary Plugins

Example entry for `revolutionEDA_plugins/plugins.json`:

```json
{
  "name": "myPlugin",
  "version": "1.2.0",
  "license": "Proprietary",
  "type": "binary",
  "description": "Binary plugin for accelerated analysis",
  "url": "https://raw.githubusercontent.com/<org>/revolutionEDA_plugins/main/myPlugin/myPlugin-default.zip",
  "binary_urls": {
    "linux-x86_64-py313": "https://raw.githubusercontent.com/<org>/revolutionEDA_plugins/main/myPlugin/myPlugin-linux-x86_64-py313.zip",
    "linux-x86_64-py314": "https://raw.githubusercontent.com/<org>/revolutionEDA_plugins/main/myPlugin/myPlugin-linux-x86_64-py314.zip",
    "windows-amd64-py314": "https://raw.githubusercontent.com/<org>/revolutionEDA_plugins/main/myPlugin/myPlugin-windows-amd64-py314.zip",
    "darwin-arm64-py313": "https://raw.githubusercontent.com/<org>/revolutionEDA_plugins/main/myPlugin/myPlugin-darwin-arm64-py313.zip"
  }
}
```

## Build Strategy

Binary plugins are Python-version-specific for Revolution EDA.

Build and publish separate packages for each supported Python version (for example `py313`, `py314`).

If you use compiled Python extensions, ensure build matrix includes:
- All supported OS targets
- All supported CPU architectures
- All supported Python versions for Revolution EDA releases

## Versioning Strategy for Binary Plugins

Use semantic versions and keep plugin version aligned across:
- Plugin-local `config.json` (`plugin_version`)
- Registry `plugins.json` (`version`)
- ZIP filename tags (recommended)

When binary compatibility changes across Python/runtime versions, bump at least the minor version (or major for breaking changes).

## Validation Checklist Before Publishing

- ZIP extracts into one folder named exactly as plugin package.
- Folder contains `__init__.py` and valid `config.json`.
- Callback functions referenced by `config.json` are importable.
- Binary dependencies are present beside modules or correctly resolved at runtime.
- Each `binary_urls` key matches an actual published ZIP.
- Fallback `url` is valid.
- Fresh install test passes via `Tools -> Plugins -> Setup Plugins...`.
- Plugin loads without errors in `reveda.log`.

## Common Binary Plugin Failures

`ImportError` after install:
- Wrong Python ABI or missing shared library dependency.

Plugin installs but does not appear:
- ZIP extracted into wrong directory layout.

Menu action missing:
- `config.json` callback name does not match exported function in module.

Wrong package selected from registry:
- `binary_urls` key does not match actual `platform.system()`/`platform.machine()` values.

## Quick Local Probe Script

Use this to see what key your machine expects:

```python
import platform
import sys

system = platform.system().lower()
arch = platform.machine().lower()
py_tag = f"py{sys.version_info.major}{sys.version_info.minor}"

print("Expected primary key:", f"{system}-{arch}-{py_tag}")
print("Fallback keys:", f"{system}-{arch}", system)
```

## Publishing Flow to `revolutionEDA_plugins`

1. Build and package ZIP files per target.
2. Upload ZIP files into plugin folder in `https://github.com/eskiyerli/revolutionEDA_plugins`.
3. Add or update plugin entry in repository `plugins.json`.
4. Open pull request with tested OS/arch/Python matrix.
5. After merge, verify install from Revolution EDA Plugin Registry UI.
