#    "Commons Clause" License Condition v1.0
#   #
#    The Software is provided to you by the Licensor under the License, as defined
#    below, subject to the following condition.
#
#    Without limiting other conditions in the License, the grant of rights under the
#    License will not include, and the License does not grant to you, the right to
#    Sell the Software.
#
#    For purposes of the foregoing, "Sell" means practicing any or all of the rights
#    granted to you under the License to provide to third parties, for a fee or other
#    consideration (including without limitation fees for hosting) a product or service whose value
#    derives, entirely or substantially, from the functionality of the Software. Any
#    license notice or attribution required by the License must also include this
#    Commons Clause License Condition notice.
#
#   Add-ons and extensions developed for this software may be distributed
#   under their own separate licenses.
#
#    Software: Revolution EDA
#    License: Mozilla Public License 2.0
#    Licensor: Revolution Semiconductor (Registered in the Netherlands)
#

"""
Schema validation for Revolution EDA JSON design files.

Provides JSON Schema definitions and validation utilities for symbol,
schematic, and layout files. Validates files on load to provide clear
error messages instead of cryptic exceptions.

The canonical JSON Schema files are stored alongside this module in the
``schemas/`` directory.  They can be referenced from design JSON files
using the standard ``$schema`` property pointing to the schema ``$id``:

  - Symbol:    https://reveda.org/schemas/v1.0/symbol.schema.json
  - Schematic: https://reveda.org/schemas/v1.0/schematic.schema.json
  - Layout:    https://reveda.org/schemas/v1.0/layout.schema.json

Or by relative path to the bundled schema files.
"""

import json
import logging
import pathlib
from typing import Any, List, Optional, Tuple

import jsonschema
from jsonschema import ValidationError, SchemaError

logger = logging.getLogger(__name__)

# Current schema version for future migration support
SCHEMA_VERSION = "1.0"

# Maximum number of validation errors to report before truncating
MAX_VALIDATION_ERRORS = 10

# ---------------------------------------------------------------------------
# Load schemas from JSON files
# ---------------------------------------------------------------------------

_SCHEMAS_DIR = pathlib.Path(__file__).parent / "schemas"


def _load_schema(filename: str) -> dict:
    """Load a JSON schema file from the schemas directory."""
    schema_path = _SCHEMAS_DIR / filename
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file {schema_path}: {e}")
        raise


SYMBOL_FILE_SCHEMA = _load_schema("symbol.schema.json")
SCHEMATIC_FILE_SCHEMA = _load_schema("schematic.schema.json")
LAYOUT_FILE_SCHEMA = _load_schema("layout.schema.json")

# Mapping from viewType to schema
_VIEW_TYPE_SCHEMAS = {
    "symbol": SYMBOL_FILE_SCHEMA,
    "schematic": SCHEMATIC_FILE_SCHEMA,
    "layout": LAYOUT_FILE_SCHEMA,
}

# Public helper: path to the schemas directory for tools that need it
SCHEMAS_DIR = _SCHEMAS_DIR


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


class DesignFileValidationError(Exception):
    """Raised when a design file fails schema validation.

    Attributes:
        file_path: Path to the invalid file (if available).
        errors: List of human-readable error descriptions.
    """

    def __init__(self, message: str, file_path: str = "",
                 errors: Optional[List[str]] = None):
        super().__init__(message)
        self.file_path = file_path
        self.errors = errors or []


def _format_validation_error(error: ValidationError) -> str:
    """Convert a jsonschema ValidationError to a human-friendly message."""
    path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
    return f"At '{path}': {error.message}"


def validate_design_data(
    data: Any,
    file_path: str = "",
    strict: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate loaded JSON data against the appropriate design file schema.

    Performs structural validation of the top-level array, view header,
    and grid settings. Individual item validation is done only in strict mode
    to allow forward-compatible file loading.

    Args:
        data: The parsed JSON data (expected to be a list).
        file_path: Optional file path for error reporting.
        strict: If True, validate every item against the item schema.
                If False, only validate the structure/header (faster).

    Returns:
        A tuple of (is_valid, error_messages).
        If is_valid is True, error_messages is empty.
    """
    errors: List[str] = []

    # Basic structure check
    if not isinstance(data, list):
        errors.append(
            f"Design file must be a JSON array, got {type(data).__name__}"
        )
        return False, errors

    if len(data) < 2:
        errors.append(
            "Design file must contain at least a view header and grid "
            "settings (minimum 2 elements)"
        )
        return False, errors

    # Validate view header
    view_header = data[0]
    if not isinstance(view_header, dict):
        errors.append(
            f"First element (view header) must be an object, "
            f"got {type(view_header).__name__}"
        )
        return False, errors

    view_type = view_header.get("viewType")
    if view_type not in ("symbol", "schematic", "layout"):
        errors.append(
            f"Invalid or missing 'viewType' in header. "
            f"Expected 'symbol', 'schematic', or 'layout', got: {view_type!r}"
        )
        return False, errors

    # Validate grid settings
    grid_settings = data[1]
    if grid_settings is not None and not isinstance(grid_settings, dict):
        errors.append(
            f"Second element (grid settings) must be an object or null, "
            f"got {type(grid_settings).__name__}"
        )
        return False, errors

    if grid_settings and "snapGrid" in grid_settings:
        snap_grid = grid_settings["snapGrid"]
        if not (isinstance(snap_grid, (list, tuple)) and len(snap_grid) == 2):
            errors.append(
                f"'snapGrid' must be a 2-element array, got: {snap_grid!r}"
            )
            return False, errors

    # Validate items in strict mode
    if strict:
        schema = _VIEW_TYPE_SCHEMAS.get(view_type)
        if schema:
            try:
                jsonschema.validate(instance=data, schema=schema)
            except ValidationError as e:
                # Collect errors for user feedback
                validator = jsonschema.Draft7Validator(schema)
                for i, err in enumerate(validator.iter_errors(data)):
                    if i >= MAX_VALIDATION_ERRORS:
                        errors.append("... (additional errors truncated)")
                        break
                    errors.append(_format_validation_error(err))
                return False, errors
            except SchemaError as e:
                # Internal schema error - log but don't block loading
                logger.warning(f"Schema definition error: {e.message}")

    # Non-strict item validation: check that items have a 'type' field
    if not strict:
        for idx, item in enumerate(data[2:], start=2):
            if isinstance(item, dict) and "type" not in item:
                errors.append(
                    f"Item at index {idx} is missing required 'type' field"
                )

    if errors:
        return False, errors

    return True, []


def validate_design_file(
    data: Any,
    view_type: str,
    file_path: str = "",
    strict: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate design file data with an expected view type.

    This is a convenience wrapper that also verifies the viewType matches
    the expected type.

    Args:
        data: The parsed JSON data.
        view_type: Expected view type ('symbol', 'schematic', 'layout').
        file_path: Optional file path for error reporting.
        strict: If True, run full jsonschema validation.

    Returns:
        A tuple of (is_valid, error_messages).
    """
    is_valid, errors = validate_design_data(data, file_path, strict)
    if not is_valid:
        return False, errors

    actual_type = data[0].get("viewType")
    if actual_type != view_type:
        return False, [
            f"Expected view type '{view_type}', but file contains "
            f"'{actual_type}'"
        ]

    return True, []


def get_schema_version(data: Any) -> Optional[str]:
    """Extract the schema version from design file data.

    Returns None if no schema version is present (pre-versioning files).
    """
    if isinstance(data, list) and len(data) >= 1 and isinstance(data[0], dict):
        return data[0].get("schemaVersion")
    return None
