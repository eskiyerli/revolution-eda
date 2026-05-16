# Commercial Plugin Development Guide for Revolution EDA

## Overview

This guide provides comprehensive instructions for third-party developers who want to create and distribute commercial plugins for Revolution EDA. Commercial plugins integrate with Revolution Semiconductor's licensing infrastructure and plugin registry.

## Table of Contents

1. [Plugin Architecture](#plugin-architecture)
2. [Licensing Infrastructure](#licensing-infrastructure)
3. [Plugin Registry Integration](#plugin-registry-integration)
4. [Implementation Guide](#implementation-guide)
5. [Distribution and Packaging](#distribution-and-packaging)
6. [API Reference](#api-reference)
7. [Best Practices](#best-practices)
8. [Support and Contact](#support-and-contact)

---

## Plugin Architecture

### Plugin Structure

A commercial plugin must follow this directory structure:

```
your_plugin/
├── __init__.py              # Plugin entry point with license validation
├── config.json              # Plugin configuration and metadata
├── license.json             # License configuration (provided by Revolution Semiconductor)
├── your_module.py           # Main functionality
├── gui/                     # GUI components (if applicable)
├── backend/                 # Backend logic
├── resources/               # Icons, images, etc.
└── README.md                # Plugin documentation
```

### Required Files

#### 1. `__init__.py`
The entry point that validates licenses before loading the plugin.

#### 2. `config.json`
Plugin metadata that the host application reads to integrate menus and functionality.

#### 3. `license.json`
Provided by Revolution Semiconductor after partnership agreement.

---

## Licensing Infrastructure

### Overview

Revolution EDA uses a compiled licensing module (`revedaLicense`) that provides:

- **License validation**: Verify if a user has a valid license for your plugin
- **License activation**: Activate license keys provided to customers
- **Hardware binding**: Licenses can be tied to specific machines
- **Trial management**: Support for trial periods and feature restrictions

### License Types

Revolution Semiconductor supports the following license models:

| License Type | Description | Use Case |
|-------------|-------------|----------|
| `perpetual` | One-time purchase, permanent license | Individual users |
| `subscription` | Monthly/annual recurring license | Teams, enterprises |
| `trial` | Time-limited evaluation license | Evaluation period |
| `floating` | Shared license pool for organizations | Enterprise teams |
| `node-locked` | Tied to specific hardware | Secure environments |

### License Validation API

The licensing infrastructure provides these key functions:

```python
# Import the license manager
from revedaLicense.licenseManager import (
    has_valid_license,      # Check if license is valid
    get_license_info,       # Get license details
    activate_license,       # Activate a license key
    get_trial_status,       # Check trial expiration
    validate_hardware,      # Validate hardware binding
)
```

#### Function Reference

**`has_valid_license(plugin_name: str) -> bool`**

Checks if the current user has a valid license for the specified plugin.

```python
try:
    from revedaLicense.licenseManager import has_valid_license
except ImportError:
    raise RuntimeError(
        "The 'revedaLicense' module is required. "
        "Please install Revolution EDA with commercial plugin support."
    )

if not has_valid_license("yourPlugin"):
    raise RuntimeError(
        "Your plugin requires a valid license. "
        "Please activate your license in Revolution EDA (Plugins → License)."
    )
```

**`get_license_info(plugin_name: str) -> dict`**

Returns detailed license information including type, expiration, features.

```python
license_info = get_license_info("yourPlugin")
# Returns:
# {
#     "type": "subscription",
#     "expires": "2026-12-31",
#     "features": ["feature1", "feature2"],
#     "trial": False,
#     "status": "active"
# }
```

**`activate_license(plugin_name: str, license_key: str) -> bool`**

Activates a license key for the specified plugin.

```python
success = activate_license("yourPlugin", "XXXX-XXXX-XXXX-XXXX")
```

### Required License Validation Pattern

Every commercial plugin must implement this pattern in `__init__.py`:

```python
"""
Your Plugin Name
Copyright (c) [Year] [Your Company]
All rights reserved.

This plugin requires a valid commercial license from Revolution Semiconductor.
"""

__author__ = "Your Company"
__copyright__ = "Copyright [Year] Your Company"
__license__ = "Commercial"
__version__ = "1.0.0"
__status__ = "Production"

_PLUGIN_NAME = "yourPlugin"


def _require_license() -> None:
    """Validate license before allowing plugin to load.
    
    This function is called during plugin initialization. If the license
    is invalid or missing, it raises RuntimeError to prevent the plugin
    from loading.
    """
    try:
        from revedaLicense.licenseManager import has_valid_license
    except ImportError:
        raise RuntimeError(
            f"The 'revedaLicense' module is required to use {_PLUGIN_NAME}. "
            "Please reinstall Revolution EDA with commercial plugin support."
        )
    
    if not has_valid_license(_PLUGIN_NAME):
        raise RuntimeError(
            f"{_PLUGIN_NAME} requires a valid commercial license.\n"
            "Please activate your license key in Revolution EDA "
            "(Plugins → License → Activate).\n"
            "If you don't have a license, visit: https://your-payment-url.com"
        )


# Validate license on import - this prevents unauthorized use
_require_license()

# Now safe to import and expose your plugin functionality
from .your_module import YourMainClass
from .gui.your_dialog import YourDialog

__all__ = ["YourMainClass", "YourDialog"]
```

---

## Plugin Registry Integration

### Registry Overview

The Revolution EDA Plugin Registry (`https://plugins.reveda.eu/plugins.json`) is the central repository for all available plugins. Users browse and install plugins through the Plugin Registry window.

### Registry Entry Format

To be included in the registry, your plugin needs this JSON structure:

```json
{
  "name": "yourPlugin",
  "version": "1.0.0",
  "description": "Brief description of what your plugin does",
  "type": "binary",
  "license": "Commercial",
  "license_required": true,
  "payment_url": "https://your-payment-gateway.com/checkout",
  "author": "Your Company Name",
  "website": "https://your-website.com",
  "support_email": "support@your-company.com",
  "download_count": 0,
  "min_reveda_version": "0.8.11",
  "max_reveda_version": null,
  "binary_urls": {
    "linux-x86_64-py3.12": "https://plugins.reveda.eu/yourPlugin/linux-x86_64-py3.12.zip",
    "linux-x86_64-py3.13": "https://plugins.reveda.eu/yourPlugin/linux-x86_64-py3.13.zip",
    "linux-x86_64-py3.14": "https://plugins.reveda.eu/yourPlugin/linux-x86_64-py3.14.zip",
    "windows-amd64-py3.12": "https://plugins.reveda.eu/yourPlugin/windows-amd64-py3.12.zip",
    "macos-x86_64-py3.12": "https://plugins.reveda.eu/yourPlugin/macos-x86_64-py3.12.zip"
  },
  "changelog": [
    {
      "version": "1.0.0",
      "date": "2026-05-16",
      "changes": ["Initial release"]
    }
  ],
  "tags": ["simulation", "analysis", "custom-tag"],
  "featured": false
}
```

### Platform Key Format

Binary URLs use platform-specific keys:

```
{os}-{arch}-py{major}.{minor}
```

Examples:
- `linux-x86_64-py3.12` - Linux x86_64, Python 3.12
- `linux-x86_64-py3.13` - Linux x86_64, Python 3.13
- `windows-amd64-py3.12` - Windows AMD64, Python 3.12
- `macos-x86_64-py3.12` - macOS x86_64, Python 3.12
- `macos-arm64-py3.12` - macOS Apple Silicon, Python 3.12

### Publishing to Registry

To publish your plugin:

1. **Partnership Agreement**: Contact Revolution Semiconductor to establish a commercial plugin partnership
2. **License Integration**: Implement revedaLicense validation in your plugin
3. **Build Binaries**: Compile platform-specific binaries for supported platforms
4. **Upload Artifacts**: Provide download URLs hosted on Revolution's infrastructure or your own CDN
5. **Registry Update**: Revolution Semiconductor adds your plugin entry to `plugins.json`

---

## Implementation Guide

### Step 1: Set Up Development Environment

```bash
# Install Revolution EDA with development dependencies
pip install -e /path/to/revolution-eda

# Set plugin path to your development directory
export REVEDA_PLUGIN_PATH=/path/to/your/plugin/dev
```

### Step 2: Create Plugin Configuration

**`config.json`**

```json
{
  "plugin_name": "yourPlugin",
  "plugin_version": "1.0.0",
  "description": "Your plugin description",
  "license": "Commercial",
  "payment_url": "https://your-checkout-url.com",
  "author": "Your Company",
  "copyright": "Your Company",
  "website": "https://your-website.com",
  "min_reveda_version": "0.8.11",
  "menu_items": [
    {
      "location": "menuBar",
      "menu": "Tools",
      "action": "yourAction",
      "text": "Your Menu Item",
      "icon": ":/icons/your-icon.png",
      "callback": "your_callback_function",
      "shortcut": "Ctrl+Shift+Y",
      "checked": 0,
      "apply": [
        "schematicEditor",
        "symbolEditor",
        "layoutEditor"
      ]
    }
  ],
  "toolbar_items": [
    {
      "action": "yourAction",
      "text": "Your Tool",
      "icon": ":/icons/your-tool.png",
      "callback": "your_callback_function",
      "apply": ["schematicEditor"]
    }
  ],
  "viewTypes": []
}
```

### Step 3: Implement License Validation

**`__init__.py`**

```python
"""
Your Plugin for Revolution EDA

Copyright (c) 2026 Your Company
All rights reserved.

This plugin requires a valid commercial license from Revolution Semiconductor.
"""

import logging

logger = logging.getLogger(__name__)

__author__ = "Your Company"
__copyright__ = "Copyright 2026 Your Company"
__license__ = "Commercial"
__version__ = "1.0.0"
__status__ = "Production"

_PLUGIN_NAME = "yourPlugin"


def _require_license() -> None:
    """Validate commercial license before loading plugin."""
    try:
        from revedaLicense.licenseManager import (
            has_valid_license,
            get_license_info,
        )
    except ImportError:
        logger.error("revedaLicense module not found")
        raise RuntimeError(
            f"'{_PLUGIN_NAME}' requires the Revolution EDA licensing module.\n"
            "Please install Revolution EDA with commercial plugin support."
        )
    
    if not has_valid_license(_PLUGIN_NAME):
        logger.error(f"No valid license found for {_PLUGIN_NAME}")
        raise RuntimeError(
            f"'{_PLUGIN_NAME}' requires a valid commercial license.\n\n"
            "To activate your license:\n"
            "1. Open Revolution EDA\n"
            "2. Go to Plugins → License → Activate\n"
            "3. Enter your license key\n\n"
            "To purchase a license, visit:\n"
            "https://your-payment-url.com"
        )
    
    # Optional: Check license features
    license_info = get_license_info(_PLUGIN_NAME)
    logger.info(f"License validated: {license_info['type']} "
                f"(expires: {license_info.get('expires', 'N/A')})")


# Validate on import - prevents unauthorized loading
_require_license()

# Now safe to expose plugin functionality
from .main_module import YourPluginMain
from .gui.settings_dialog import SettingsDialog

__all__ = ["YourPluginMain", "SettingsDialog"]
```

### Step 4: Implement Plugin Functionality

**`main_module.py`**

```python
"""
Main plugin functionality.

License validation already performed in __init__.py,
so we can safely implement features here.
"""

from PySide6.QtCore import QObject


class YourPluginMain(QObject):
    """Main plugin class that integrates with Revolution EDA."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Your initialization code
        pass
    
    def run_analysis(self, data):
        """Example plugin function."""
        # Implementation
        pass
```

### Step 5: Create GUI Components (Optional)

**`gui/settings_dialog.py`**

```python
"""
Plugin settings dialog.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class SettingsDialog(QDialog):
    """Settings dialog for your plugin."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Your Plugin Settings")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Your Plugin Settings"))
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)
```

---

## Distribution and Packaging

### Building Platform-Specific Binaries

Commercial plugins should be compiled to protect source code. Use Nuitka or similar tools:

```bash
# Install Nuitka
pip install nuitka

# Build compiled plugin
python -m nuitka \
    --module \
    --include-package=your_plugin \
    --remove-output \
    --output-dir=dist \
    your_plugin/

# Create platform-specific zip
cd dist
zip -r your_plugin_linux_x86_64_py3.12.zip your_plugin/
```

### Packaging Structure

The final package should be a zip file containing:

```
your_plugin_platform_py3.XX.zip
├── your_plugin/
│   ├── __init__.py          # License validation + entry point
│   ├── config.json          # Plugin configuration
│   ├── license.json         # License config (provided by Revolution)
│   ├── *.so / *.pyd         # Compiled extension modules
│   └── ...                  # Other plugin files
```

### Distribution Options

1. **Official Registry**: Distributed through `plugins.reveda.eu`
   - Maximum visibility
   - Integrated with Revolution EDA installer
   - Managed by Revolution Semiconductor

2. **Private Distribution**: Self-hosted or enterprise deployment
   - Custom license server
   - Enterprise license management
   - Requires coordination with Revolution Semiconductor

---

## API Reference

### revedaLicense.licenseManager

#### `has_valid_license(plugin_name: str) -> bool`

Checks if a valid license exists for the specified plugin.

**Parameters:**
- `plugin_name` (str): The unique plugin identifier

**Returns:**
- `bool`: True if valid license exists, False otherwise

**Raises:**
- `ImportError`: If revedaLicense module is not installed

**Example:**
```python
from revedaLicense.licenseManager import has_valid_license

if has_valid_license("yourPlugin"):
    print("License is valid")
else:
    print("License is invalid or expired")
```

---

#### `get_license_info(plugin_name: str) -> dict`

Retrieves detailed information about the current license.

**Parameters:**
- `plugin_name` (str): The unique plugin identifier

**Returns:**
- `dict` with keys:
  - `type` (str): License type (perpetual, subscription, trial, floating, node-locked)
  - `status` (str): active, expired, invalid, trial
  - `expires` (str | None): Expiration date in ISO format
  - `features` (list[str]): Enabled feature flags
  - `trial` (bool): Whether this is a trial license
  - `activation_date` (str): When the license was activated
  - `hardware_id` (str | None): Hardware binding identifier

**Example:**
```python
from revedaLicense.licenseManager import get_license_info

info = get_license_info("yourPlugin")
print(f"License type: {info['type']}")
print(f"Expires: {info.get('expires', 'Never')}")
print(f"Features: {', '.join(info['features'])}")
```

---

#### `activate_license(plugin_name: str, license_key: str) -> bool`

Activates a license key for the specified plugin.

**Parameters:**
- `plugin_name` (str): The unique plugin identifier
- `license_key` (str): The license key provided to the customer

**Returns:**
- `bool`: True if activation successful, False otherwise

**Example:**
```python
from revedaLicense.licenseManager import activate_license

success = activate_license("yourPlugin", "XXXX-XXXX-XXXX-XXXX")
if success:
    print("License activated successfully")
else:
    print("Invalid license key")
```

---

#### `get_trial_status(plugin_name: str) -> dict`

Gets trial license status and remaining time.

**Parameters:**
- `plugin_name` (str): The unique plugin identifier

**Returns:**
- `dict` with keys:
  - `is_trial` (bool): Whether currently in trial
  - `days_remaining` (int): Days left in trial (0 if expired)
  - `trial_started` (str): Trial start date
  - `trial_duration` (int): Total trial duration in days

**Example:**
```python
from revedaLicense.licenseManager import get_trial_status

status = get_trial_status("yourPlugin")
if status['is_trial']:
    print(f"Trial expires in {status['days_remaining']} days")
```

---

#### `validate_hardware() -> bool`

Validates that the current hardware matches the license binding.

**Returns:**
- `bool`: True if hardware is valid, False otherwise

**Example:**
```python
from revedaLicense.licenseManager import validate_hardware

if not validate_hardware():
    print("License is bound to different hardware")
```

---

## Best Practices

### 1. License Validation

- **Always validate early**: Call `_require_license()` in `__init__.py` before exposing any functionality
- **Fail hard**: Raise `RuntimeError` on license failure - don't silently disable features
- **Clear messages**: Provide helpful error messages with activation instructions
- **Graceful degradation**: If possible, show a read-only/demo mode when license expires

### 2. Code Protection

- **Compile your plugin**: Use Nuitka or Cython to protect source code
- **Obfuscate strings**: Don't hardcode license logic or URLs
- **Verify checksums**: Check plugin integrity on load

### 3. User Experience

- **Clear pricing**: Display prices and purchase links prominently
- **Trial availability**: Offer time-limited trials when possible
- **Easy activation**: Simple license key entry process
- **Help documentation**: Provide clear activation instructions

### 4. Error Handling

```python
def _require_license():
    try:
        from revedaLicense.licenseManager import has_valid_license
    except ImportError as e:
        raise RuntimeError(
            f"Your plugin requires the Revolution EDA licensing module. "
            f"Error: {e}"
        ) from e
    
    try:
        if not has_valid_license("yourPlugin"):
            raise RuntimeError(
                "Your plugin requires a valid commercial license. "
                "Please activate your license in Revolution EDA."
            )
    except Exception as e:
        logger.error(f"License validation failed: {e}")
        raise RuntimeError(f"License validation failed: {e}") from e
```

### 5. Version Compatibility

```json
{
  "min_reveda_version": "0.8.11",
  "max_reveda_version": "0.9.0",
  "python_versions": ["3.12", "3.13", "3.14"]
}
```

### 6. Testing

Test your plugin under these conditions:

1. **No license**: Should fail with clear error message
2. **Invalid license**: Should fail with activation prompt
3. **Expired license**: Should fail with renewal prompt
4. **Trial license**: Should work with trial limitations
5. **Valid license**: Should work with full functionality
6. **Missing revedaLicense module**: Should fail with install instructions

---

## Configuration Reference

### `config.json` Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plugin_name` | string | Yes | Unique plugin identifier (alphanumeric + underscore) |
| `plugin_version` | string | Yes | Semantic version (e.g., "1.0.0") |
| `description` | string | Yes | Short description for registry |
| `license` | string | Yes | License type: "Commercial", "Proprietary", "MIT", etc. |
| `payment_url` | string | Yes* | Payment/checkout URL (*required for Commercial) |
| `author` | string | Yes | Plugin author/company name |
| `copyright` | string | Yes | Copyright holder name |
| `website` | string | No | Plugin website URL |
| `support_email` | string | No | Support contact email |
| `min_reveda_version` | string | Yes | Minimum Revolution EDA version required |
| `max_reveda_version` | string | No | Maximum compatible version (null for no limit) |
| `menu_items` | array | No | Menu integrations |
| `toolbar_items` | array | No | Toolbar integrations |
| `viewTypes` | array | No | Custom view types |

### Menu Item Configuration

```json
{
  "location": "menuBar",
  "menu": "Tools",
  "action": "uniqueActionName",
  "text": "Menu Item Text",
  "icon": ":/icons/icon.png",
  "callback": "python_function_name",
  "shortcut": "Ctrl+Shift+T",
  "checked": 0,
  "apply": ["schematicEditor", "layoutEditor"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | string | Yes | "menuBar" or "contextMenu" |
| `menu` | string | Yes | Parent menu name |
| `action` | string | Yes | Unique action identifier |
| `text` | string | Yes | Display text |
| `icon` | string | No | Icon resource path |
| `callback` | string | Yes | Python function to call |
| `shortcut` | string | No | Keyboard shortcut |
| `checked` | integer | No | Checkable state (0=unchecked, 1=checked) |
| `apply` | array | Yes | Window types where menu appears |

**Valid `apply` values:**
- `schematicEditor` - Schematic editor
- `symbolEditor` - Symbol editor
- `layoutEditor` - Layout editor
- `SimMainWindow` - Simulation window
- `*` - All windows

---

## Troubleshooting

### Common Issues

#### "revedaLicense module not found"

**Cause**: Revolution EDA was installed without commercial plugin support.

**Solution**:
```bash
# Reinstall with license support
pip install --force-reinstall revolution-eda[commercial]

# Or download the compiled extension manually
# See: https://plugins.reveda.eu/revedaLicense/
```

#### "License validation failed"

**Cause**: License key is invalid, expired, or for different plugin.

**Solution**:
1. Check license key format
2. Verify plugin name matches license
3. Check if license is expired
4. Re-activate license in Plugins → License

#### "Plugin not showing in registry"

**Cause**: Plugin not published or registry not updated.

**Solution**:
1. Verify plugin is published to `plugins.reveda.eu`
2. Check registry URL is accessible
3. Clear plugin cache and restart Revolution EDA

---

## Support and Contact

### Getting Help

- **Documentation**: https://docs.reveda.eu/plugins
- **Developer Forum**: https://forum.reveda.eu/developers
- **Email**: plugins@reveda.eu
- **Slack**: Join #plugin-developers channel

### Partnership Inquiries

To become an official commercial plugin partner:

1. **Apply**: Send proposal to partners@reveda.eu
2. **Review**: Revolution Semiconductor reviews your plugin concept
3. **Agreement**: Sign commercial plugin partnership agreement
4. **Integration**: Implement licensing and registry integration
5. **Testing**: Beta testing with selected users
6. **Launch**: Plugin goes live in official registry

### Legal

- **Trademark**: "Revolution EDA" and "reveda" are trademarks of Revolution Semiconductor
- **License**: Your plugin's license terms must be compatible with MPL-2.0 host application
- **Compliance**: All plugins must comply with Revolution EDA's plugin developer agreement

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-16 | Initial release |

---

*Copyright (c) 2026 Revolution Semiconductor. All rights reserved.*
*This document is confidential and proprietary to Revolution Semiconductor.*
