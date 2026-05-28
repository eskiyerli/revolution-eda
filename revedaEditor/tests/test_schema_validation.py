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

"""Tests for revedaEditor.fileio.schemaValidation module."""

import pytest

from revedaEditor.fileio.schemaValidation import (
    SCHEMA_VERSION,
    validate_design_data,
    validate_design_file,
    get_schema_version,
    DesignFileValidationError,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_symbol_data():
    return [
        {"viewType": "symbol", "schemaVersion": "1.0"},
        {"snapGrid": [10, 5]},
        {"type": "rect", "rect": [0, 0, 100, 50], "loc": [10, 20],
         "ang": 0, "fl": [1, 1]},
        {"type": "pin", "st": [0, 0], "nam": "A", "pd": "input",
         "pt": "signal", "loc": [5, 5], "ang": 0, "fl": [1, 1]},
    ]


@pytest.fixture
def valid_schematic_data():
    return [
        {"viewType": "schematic", "schemaVersion": "1.0"},
        {"snapGrid": [10, 5]},
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "net1",
         "ns": 3},
        {"type": "scp", "st": [0, 0], "pn": "VDD", "pd": "input",
         "pt": "signal", "ang": 0, "fl": [1, 1]},
    ]


@pytest.fixture
def valid_layout_data():
    return [
        {"viewType": "layout", "schemaVersion": "1.0"},
        {"snapGrid": [10, 5]},
        {"type": "Rect", "tl": [0, 0], "br": [100, 50], "ln": 0,
         "ang": 0, "fl": [1, 1]},
    ]


# ---------------------------------------------------------------------------
# Tests: validate_design_data
# ---------------------------------------------------------------------------


class TestValidateDesignData:
    def test_valid_symbol(self, valid_symbol_data):
        is_valid, errors = validate_design_data(valid_symbol_data)
        assert is_valid
        assert errors == []

    def test_valid_schematic(self, valid_schematic_data):
        is_valid, errors = validate_design_data(valid_schematic_data)
        assert is_valid
        assert errors == []

    def test_valid_layout(self, valid_layout_data):
        is_valid, errors = validate_design_data(valid_layout_data)
        assert is_valid
        assert errors == []

    def test_not_a_list(self):
        is_valid, errors = validate_design_data({"viewType": "symbol"})
        assert not is_valid
        assert "JSON array" in errors[0]

    def test_empty_list(self):
        is_valid, errors = validate_design_data([])
        assert not is_valid
        assert "minimum 2 elements" in errors[0]

    def test_single_element(self):
        is_valid, errors = validate_design_data([{"viewType": "symbol"}])
        assert not is_valid
        assert "minimum 2 elements" in errors[0]

    def test_invalid_view_type(self):
        data = [{"viewType": "unknown"}, {"snapGrid": [10, 5]}]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "viewType" in errors[0]

    def test_missing_view_type(self):
        data = [{}, {"snapGrid": [10, 5]}]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "viewType" in errors[0]

    def test_non_dict_header(self):
        data = ["not a dict", {"snapGrid": [10, 5]}]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "view header" in errors[0]

    def test_invalid_grid_settings_type(self):
        data = [{"viewType": "symbol"}, "invalid"]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "grid settings" in errors[0]

    def test_invalid_snap_grid_format(self):
        data = [{"viewType": "symbol"}, {"snapGrid": [10]}]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "snapGrid" in errors[0]

    def test_null_grid_settings_is_valid(self):
        data = [{"viewType": "symbol"}, None]
        is_valid, errors = validate_design_data(data)
        assert is_valid
        assert errors == []

    def test_item_missing_type_field(self):
        data = [
            {"viewType": "symbol"},
            {"snapGrid": [10, 5]},
            {"rect": [0, 0, 100, 50]},  # missing "type"
        ]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "type" in errors[0]

    def test_minimal_valid_file(self):
        data = [{"viewType": "layout"}, {"snapGrid": [10, 5]}]
        is_valid, errors = validate_design_data(data)
        assert is_valid
        assert errors == []

    def test_legacy_file_without_schema_version(self):
        """Files without schemaVersion should still validate."""
        data = [
            {"viewType": "symbol"},
            {"snapGrid": [10, 5]},
            {"type": "rect", "rect": [0, 0, 100, 50], "loc": [10, 20]},
        ]
        is_valid, errors = validate_design_data(data)
        assert is_valid


# ---------------------------------------------------------------------------
# Tests: validate_design_file
# ---------------------------------------------------------------------------


class TestValidateDesignFile:
    def test_correct_view_type(self, valid_symbol_data):
        is_valid, errors = validate_design_file(valid_symbol_data, "symbol")
        assert is_valid
        assert errors == []

    def test_wrong_view_type(self, valid_symbol_data):
        is_valid, errors = validate_design_file(
            valid_symbol_data, "schematic"
        )
        assert not is_valid
        assert "Expected view type" in errors[0]

    def test_invalid_data_fails_before_type_check(self):
        is_valid, errors = validate_design_file([], "symbol")
        assert not is_valid


# ---------------------------------------------------------------------------
# Tests: strict validation
# ---------------------------------------------------------------------------


class TestStrictValidation:
    def test_strict_valid_symbol(self, valid_symbol_data):
        is_valid, errors = validate_design_data(
            valid_symbol_data, strict=True
        )
        assert is_valid
        assert errors == []

    def test_strict_valid_schematic(self, valid_schematic_data):
        is_valid, errors = validate_design_data(
            valid_schematic_data, strict=True
        )
        assert is_valid
        assert errors == []

    def test_strict_valid_layout(self, valid_layout_data):
        is_valid, errors = validate_design_data(
            valid_layout_data, strict=True
        )
        assert is_valid
        assert errors == []

    def test_strict_invalid_item_type(self):
        data = [
            {"viewType": "symbol"},
            {"snapGrid": [10, 5]},
            {"type": "rect", "rect": "not_an_array", "loc": [10, 20]},
        ]
        is_valid, errors = validate_design_data(data, strict=True)
        assert not is_valid
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Tests: get_schema_version
# ---------------------------------------------------------------------------


class TestGetSchemaVersion:
    def test_with_version(self):
        data = [{"viewType": "symbol", "schemaVersion": "1.0"}, {}]
        assert get_schema_version(data) == "1.0"

    def test_without_version(self):
        data = [{"viewType": "symbol"}, {}]
        assert get_schema_version(data) is None

    def test_invalid_data(self):
        assert get_schema_version("not a list") is None
        assert get_schema_version([]) is None
        assert get_schema_version([42]) is None


# ---------------------------------------------------------------------------
# Tests: DesignFileValidationError
# ---------------------------------------------------------------------------


class TestDesignFileValidationError:
    def test_error_attributes(self):
        err = DesignFileValidationError(
            "Test error",
            file_path="/tmp/test.json",
            errors=["Error 1", "Error 2"],
        )
        assert str(err) == "Test error"
        assert err.file_path == "/tmp/test.json"
        assert len(err.errors) == 2

    def test_default_errors_list(self):
        err = DesignFileValidationError("Test")
        assert err.errors == []


# ---------------------------------------------------------------------------
# Tests: Schema version constant
# ---------------------------------------------------------------------------


def test_schema_version_is_string():
    assert isinstance(SCHEMA_VERSION, str)
    assert SCHEMA_VERSION == "1.0"
