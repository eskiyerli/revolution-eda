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

import copy
import types

import orjson
import pytest

from revedaEditor.fileio.schemaValidation import (
    CURRENT_SCHEMA_VERSIONS,
    SCHEMA_VERSION,
    DesignFileValidationError,
    get_schema_version,
    make_view_header,
    prepare_design_data,
    prepare_pcell_definition,
    register_schema_migration,
    validate_design_data,
    validate_design_file,
    validate_pcell_definition,
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
        {"type": "pin", "st": [0, 0], "nam": "A", "pd": "Input",
         "pt": "Signal", "loc": [5, 5], "ang": 0, "fl": [1, 1]},
    ]


@pytest.fixture
def valid_schematic_data():
    return [
        {"viewType": "schematic", "schemaVersion": "1.0"},
        {"snapGrid": [10, 5]},
        {"type": "scn", "st": [0, 0], "end": [100, 0], "nam": "net1",
         "ns": 3},
        {"type": "scp", "st": [0, 0], "pn": "VDD", "pd": "Input",
         "pt": "Signal", "ang": 0, "fl": [1, 1]},
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

    def test_null_grid_settings_is_invalid(self):
        data = [{"viewType": "symbol"}, None]
        is_valid, errors = validate_design_data(data)
        assert not is_valid
        assert "grid settings" in errors[0]

    def test_item_missing_type_field(self):
        # Non-strict validation is header-only for speed; items without a
        # "type" are tolerated and skipped by the item factory at load time.
        data = [
            {"viewType": "symbol"},
            {"snapGrid": [10, 5]},
            {"rect": [0, 0, 100, 50]},  # missing "type"
        ]
        is_valid, errors = validate_design_data(data)
        assert is_valid
        assert errors == []

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
        is_valid, _errors = validate_design_data(data)
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
        is_valid, _errors = validate_design_file([], "symbol")
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

    def test_strict_valid_layout_path_and_label_native_encoding(self):
        data = [
            {"viewType": "layout", "schemaVersion": "1.0"},
            {"snapGrid": [10, 5]},
            {
                "type": "Path", "dfl1": [0, 0], "dfl2": [100, 0],
                "top": [0, 0], "ln": 0, "w": 10, "se": 5, "ee": 5,
                "md": 0, "nam": "", "ang": 0, "fl": [1, 1],
            },
            {
                "type": "Label", "st": [0, 0], "lt": "net", "ff": "Arial",
                "fs": "Regular", "fh": "1.0", "la": "Left", "lo": "R0",
                "ln": 0, "ang": 0, "fl": [1, 1],
            },
        ]

        is_valid, errors = validate_design_data(data, strict=True)

        assert is_valid, errors

    @pytest.mark.parametrize(
        "record",
        (
            {
                "type": "Path", "dfl1": [0, 0], "dfl2": [100, 0],
                "ln": 0, "w": 10, "se": 5, "ee": 5, "md": "0",
            },
            {
                "type": "Label", "st": [0, 0], "lt": "net", "ff": "Arial",
                "fs": "Regular", "fh": "not-a-number", "la": "Left",
                "lo": "R0", "ln": 0,
            },
        ),
    )
    def test_strict_rejects_invalid_layout_path_mode_or_label_height(self, record):
        data = [
            {"viewType": "layout", "schemaVersion": "1.0"},
            {"snapGrid": [10, 5]},
            record,
        ]

        is_valid, errors = validate_design_data(data, strict=True)

        assert not is_valid
        assert errors

    @pytest.mark.parametrize(
        "record",
        (
            {
                "type": "scp", "st": [0, 0], "pn": "In", "pd": "In",
                "pt": "Signal",
            },
            {
                "type": "scp", "st": [0, 0], "pn": "VDD", "pd": "Input",
                "pt": "signal",
            },
        ),
    )
    def test_strict_rejects_invalid_schematic_pin_direction_or_type(self, record):
        data = [
            {"viewType": "schematic", "schemaVersion": "1.0"},
            {"snapGrid": [10, 5]},
            record,
        ]

        is_valid, errors = validate_design_data(data, strict=True)

        assert not is_valid
        assert errors

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


# ---------------------------------------------------------------------------
# Tests: schema compatibility and migration contract
# ---------------------------------------------------------------------------


class TestSchemaCompatibility:
    def test_headers_are_canonical_for_ordinary_views(self):
        for viewType in ("symbol", "schematic", "layout"):
            assert make_view_header(viewType) == {
                "viewType": viewType,
                "schemaVersion": CURRENT_SCHEMA_VERSIONS[viewType],
            }

    def test_legacy_unversioned_data_is_accepted_without_mutation(self):
        data = [{"viewType": "symbol"}, {"snapGrid": [10, 5]}]
        prepared, compatibility = prepare_design_data(data, "symbol")
        assert prepared is data
        assert compatibility.sourceVersion is None
        assert compatibility.targetVersion == SCHEMA_VERSION
        assert not compatibility.migrated
        assert "schemaVersion" not in data[0]

    def test_current_version_is_accepted_without_migration(self):
        data = [{"viewType": "layout", "schemaVersion": "1.0"}, {}]
        prepared, compatibility = prepare_design_data(data, "layout")
        assert prepared is data
        assert compatibility.sourceVersion == "1.0"
        assert not compatibility.migrated

    @pytest.mark.parametrize("version", ("2.0", "unknown"))
    def test_unsupported_labelled_version_is_rejected(self, version):
        data = [{"viewType": "schematic", "schemaVersion": version}, {}]
        with pytest.raises(DesignFileValidationError):
            prepare_design_data(data, "schematic")

    def test_malformed_version_is_rejected(self):
        data = [{"viewType": "symbol", "schemaVersion": 1}, {}]
        with pytest.raises(DesignFileValidationError):
            prepare_design_data(data, "symbol")

    def test_registered_migration_is_pure_and_runs_once(self):
        source = [
            {"viewType": "symbol", "schemaVersion": "test-legacy"},
            {"snapGrid": [10, 5]},
            {"type": "unknown", "extra": {"preserve": True}},
        ]
        original = copy.deepcopy(source)

        def migration(data):
            data[1]["migrated"] = True
            return data

        register_schema_migration("symbol", "test-legacy", "1.0", migration)
        prepared, compatibility = prepare_design_data(source, "symbol")
        assert source == original
        assert prepared[0]["schemaVersion"] == "1.0"
        assert prepared[1]["migrated"] is True
        assert prepared[2] == original[2]
        assert compatibility.migrated


class TestPCellDefinitionValidation:
    def test_legacy_pcell_definition_is_accepted(self):
        data = [{"cellView": "pcell"}, {"reference": "nmos"}]
        prepared, compatibility = prepare_pcell_definition(data)
        assert prepared is data
        assert compatibility.sourceVersion is None
        assert not compatibility.migrated

    @pytest.mark.parametrize(
        "data",
        (
            [],
            [{"cellView": "pcell"}],
            [{"cellView": "layout"}, {"reference": "nmos"}],
            [{"cellView": "pcell"}, {"reference": ""}],
            [{"cellView": "pcell"}, {"reference": 42}],
        ),
    )
    def test_invalid_pcell_definition_is_rejected(self, data):
        is_valid, errors = validate_pcell_definition(data)
        assert not is_valid
        assert errors
        with pytest.raises(DesignFileValidationError):
            prepare_pcell_definition(data)


# ---------------------------------------------------------------------------
# Tests: hierarchical child-file schema enforcement
# ---------------------------------------------------------------------------


def _writeLibraryCell(tmp_path, viewName, records):
    """Minimal on-disk library: mylib/sub/<viewName>.json."""
    libDir = tmp_path / "mylib"
    cellDir = libDir / "sub"
    cellDir.mkdir(parents=True)
    (cellDir / f"{viewName}.json").write_bytes(orjson.dumps(records))
    return libDir


class TestHierarchicalSchemaEnforcement:
    """Child cellviews with an unsupported future schemaVersion must be
    rejected by every hierarchical load path, not just top-level opens."""

    def test_inst_symbol_rejects_future_symbol_version(
            self, qapp, tmp_path, monkeypatch):
        from PySide6.QtCore import QPoint
        import revedaEditor.backend.dataDefinitions as ddef
        import revedaEditor.backend.libraryMethods as libm
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene

        libDir = _writeLibraryCell(tmp_path, "symbol", [
            {"viewType": "symbol", "schemaVersion": "99.0"},
            {"snapGrid": [10, 5]},
        ])
        scene = makeSchematicScene()
        libItem = types.SimpleNamespace(libraryName="mylib")
        cellItem = types.SimpleNamespace(
            cellName="sub", parent=lambda: libItem)
        viewItem = types.SimpleNamespace(
            viewName="symbol", viewPath=libDir / "sub" / "symbol.json",
            parent=lambda: cellItem)
        scene.appMainW.libraryModel = None
        monkeypatch.setattr(libm, "findViewItem", lambda *a: viewItem)
        result = scene.instSymbol(
            ddef.viewNameTuple("mylib", "sub", "symbol"), QPoint(0, 0))
        assert result is None

    def test_inst_layout_rejects_future_layout_version(
            self, qapp, tmp_path):
        import revedaEditor.backend.dataDefinitions as ddef
        import revedaEditor.backend.libBackEnd as libb
        from revedaEditor.tests.sceneTestUtils import makeLayoutScene

        libDir = _writeLibraryCell(tmp_path, "layout", [
            {"viewType": "layout", "schemaVersion": "99.0"},
            {"snapGrid": [10, 10]},
        ])
        scene = makeLayoutScene()
        layoutTuple = ddef.viewItemTuple(
            libb.libraryItem(libDir), libb.cellItem(libDir / "sub"),
            libb.viewItem(libDir / "sub" / "layout.json"))
        assert scene.instLayout(layoutTuple) is None

    def test_symbol_factory_rejects_future_version(self, qapp, tmp_path):
        import revedaEditor.fileio.loadJSON as lj
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene

        libDir = _writeLibraryCell(tmp_path, "symbol", [
            {"viewType": "symbol", "schemaVersion": "99.0"},
            {"snapGrid": [10, 5]},
        ])
        scene = makeSchematicScene()
        scene.libraryDict = {"mylib": libDir}
        factory = lj.schematicItems(scene)
        record = {"type": "sys", "lib": "mylib", "cell": "sub",
                  "view": "symbol", "ic": 1, "nam": "I1", "ld": {},
                  "loc": [0, 0]}
        assert factory._createSymbolShape(record) is None

    def test_layout_factory_rejects_future_version(self, qapp, tmp_path):
        import revedaEditor.fileio.loadJSON as lj
        from revedaEditor.tests.sceneTestUtils import makeLayoutScene

        libDir = _writeLibraryCell(tmp_path, "layout", [
            {"viewType": "layout", "schemaVersion": "99.0"},
            {"snapGrid": [10, 10]},
        ])
        scene = makeLayoutScene()
        scene.libraryDict = {"mylib": libDir}
        factory = lj.layoutItems(scene)
        record = {"type": "Inst", "lib": "mylib", "cell": "sub",
                  "view": "layout", "loc": [0, 0], "ic": 1, "nam": "I1"}
        assert factory.createLayoutInstance(record) is None
