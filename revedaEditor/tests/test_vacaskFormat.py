# SPDX-License-Identifier: MPL-2.0
#
# Revolution EDA
# Copyright (c) 2026 Revolution Semiconductor

"""Tests for the Qt-free VACASK formatter (vacaskFormat + recordsNetlist).

Unit tests exercise the formatter directly on InstanceIR inputs; the
parity test drives the same topology through the interactive
``vacaskNetlist`` (schematicSymbol) and the headless ``records_to_ir``
adapter and asserts identical lines.
"""

import json
import types

import pytest

from revedaEditor.netlisting import recordsNetlist, vacaskFormat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RES_ATTRS = {
    "VacaskNetlistLine": "@instName ( %pinOrder ) res r=@R $mfactor=@M",
    "pinOrder": "PLUS, MINUS",
    "VacaskModelLine": "model res resistor",
    "VacaskLoadFile": "resistor.osdi",
}
_RES_LABEL_DEFS = {
    "@instName": "[@instName]",
    "@cellName": "[@cellName]",
    "@R": "[@R:R=%:R=1k]",
    "@M": "[@M:M=%:M=1]",
}
_RES_LABELS = {
    "@instName": "I1", "@cellName": "res", "@R": "1k", "@M": "1",
}


def _res_ir(name="I1", pin_nets=(("PLUS", "in"), ("MINUS", "out")),
            labels=None, attrs=None):
    return vacaskFormat.InstanceIR(
        name=name,
        attrs=dict(_RES_ATTRS if attrs is None else attrs),
        labels=dict(_RES_LABELS if labels is None else labels),
        pinNets=list(pin_nets),
    )


def _fmt(ir, line_key="VacaskNetlistLine", **kwargs):
    warnings = []
    lines = vacaskFormat.format_instance_lines(
        ir, line_key, warn=warnings.append, **kwargs)
    return lines, warnings


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("a", "a"), ("a<0>", "'a<0>'"), ("a<0:3>", "'a<0:3>'"),
])
def test_quote_id(name, expected):
    assert vacaskFormat.quote_id(name) == expected


@pytest.mark.parametrize("name,expected", [
    ("scalar", ("scalar", (-1, -1))),
    ("bus<5>", ("bus", (5, 5))),
    ("net<0:3>", ("net", (0, 3))),
    ("net<7:0>", ("net", (7, 0))),
])
def test_parse_array_notation(name, expected):
    assert vacaskFormat.parse_array_notation(name) == expected


def test_expand_pin_names():
    assert vacaskFormat.expand_pin_names(
        ["a<0:1>", "b"]) == "'a<0>' 'a<1>' b"
    assert vacaskFormat.expand_pin_names(
        ["a<3:0>"]) == "'a<3>' 'a<2>' 'a<1>' 'a<0>'"


@pytest.mark.parametrize("value,expected", [
    ("1.2V", "1.2"), ("1MHz", "1M"), ("1mV", "1m"),
    ("1nA", "1n"), ("10k", "10k"), ("4.7u", "4.7u"),
    ("{vin*2}", "{vin*2}"), ("0.9", "0.9"), ("1meg", "1meg"),
])
def test_vacask_literal(value, expected):
    assert vacaskFormat.vacask_literal(value) == expected


# ---------------------------------------------------------------------------
# format_instance_lines
# ---------------------------------------------------------------------------

def test_scalar_line():
    lines, warnings = _fmt(_res_ir())
    assert lines == ["I1 ( in out ) res r=1k $mfactor=1"]
    assert not warnings


def test_missing_param_stripped():
    labels = dict(_RES_LABELS)
    del labels["@M"]
    lines, _ = _fmt(_res_ir(labels=labels))
    assert lines == ["I1 ( in out ) res r=1k"]


def test_brace_expression_stripped():
    labels = dict(_RES_LABELS)
    labels["@R"] = "{rval}"
    lines, _ = _fmt(_res_ir(labels=labels))
    assert lines == ["I1 ( in out ) res r=rval $mfactor=1"]


def test_global_nets_processed():
    tracker = vacaskFormat._GlobalTracker()
    lines, _ = _fmt(_res_ir(pin_nets=(("PLUS", "vdd!"), ("MINUS", "gnd!"))),
                    globals_tracker=tracker)
    assert lines == ["I1 ( vdd gnd ) res r=1k $mfactor=1"]
    assert tracker.globalNets == {"vdd"}
    assert tracker.groundNets == {"gnd"}


def test_array_expansion():
    lines, _ = _fmt(_res_ir(
        name="I1<0:1>",
        pin_nets=(("PLUS", "in<0:1>"), ("MINUS", "out"))))
    assert lines == ["'I1<0>' ( 'in<0>' out ) res r=1k $mfactor=1",
                     "'I1<1>' ( 'in<1>' out ) res r=1k $mfactor=1"]


def test_vector_notation_preserved():
    lines, _ = _fmt(_res_ir(
        name="I1<0:1>",
        pin_nets=(("PLUS", "in<0:1>"), ("MINUS", "out<0:1>"))))
    assert lines == [
        "'I1<0:1>' ( 'in<0:1>' 'out<0:1>' ) res r=1k $mfactor=1"]


def test_lvs_pin_order_reorders():
    attrs = dict(_RES_ATTRS)
    attrs["lvsPinOrder"] = "MINUS, PLUS"
    attrs["lvsNetlistLine"] = "@instName ( %lvsPinOrder ) res"
    lines, _ = _fmt(_res_ir(attrs=attrs), line_key="lvsNetlistLine")
    assert lines == ["I1 ( out in ) res"]


def test_missing_template_warns():
    lines, warnings = _fmt(_res_ir(attrs={}))
    assert lines == []
    assert warnings and "VacaskNetlistLine" in warnings[0]


def test_strict_tokens_rejects_dangling():
    # A bare unresolved token survives PARAM_RE (unlike name=@x pairs).
    ir = _res_ir(attrs={"VacaskNetlistLine":
                        "@instName ( %pinOrder ) res @NOSUCH"})
    lines, warnings = _fmt(ir, strict_tokens=True)
    assert lines == []
    assert warnings and "unresolved token" in warnings[0]


def test_no_instname_label_returns_empty():
    labels = dict(_RES_LABELS)
    del labels["@instName"]
    lines, warnings = _fmt(_res_ir(labels=labels))
    assert lines == [] and warnings


# ---------------------------------------------------------------------------
# resolve_label_values
# ---------------------------------------------------------------------------

def test_label_value_precedence():
    out = vacaskFormat.resolve_label_values(
        _RES_LABEL_DEFS,
        instance_values={"r": "2k"},
        typed_defaults={"@r": "5k", "@m": "3"})
    assert out["@R"] == "2k"
    assert out["@M"] == "3"
    assert out["@instName"] == ""


def test_label_value_falls_back_to_nlp_default():
    out = vacaskFormat.resolve_label_values(_RES_LABEL_DEFS, {})
    assert out["@R"] == "1k" and out["@M"] == "1"


# ---------------------------------------------------------------------------
# DeckCollector / render
# ---------------------------------------------------------------------------

def test_collector_model_dedupe():
    deck = vacaskFormat.DeckCollector()
    deck.add_model_line("model res resistor")
    deck.add_model_line("model res resistor  # dup")
    assert deck.modelLines == {"model res resistor"}


def test_collector_osdi_vs_path_load():
    deck = vacaskFormat.DeckCollector()
    deck.collect_symbol_directives({"VacaskLoadFile": "resistor.osdi"})
    deck.collect_symbol_directives({"VacaskLoadFile": "models/x.va"})
    assert deck.osdiLoadLines == {'load "resistor.osdi"'}
    assert deck.loadLines == {'load "models/x.va"'}


def test_include_lib_suppresses_model():
    deck = vacaskFormat.DeckCollector()
    deck.collect_symbol_directives({
        "VacaskIncludeLib": "devices.lib",
        "VacaskModelLine": "model res resistor"})
    assert deck.includeLibLines == {'include "devices.lib"'}
    assert not deck.modelLines


def test_include_defined_model_suppression(tmp_path):
    lib = tmp_path / "models.lib"
    lib.write_text("model res resistor\nmodel cap capacitor\n")
    deck = vacaskFormat.DeckCollector()
    deck.add_model_line("model res resistor")
    deck.add_model_line("model mydev bsim")
    deck.add_include_file(lib)
    deck.suppress_include_defined_models()
    assert deck.modelLines == {"model mydev bsim"}


def test_render_netlist_ordering():
    deck = vacaskFormat.DeckCollector()
    deck.process_global_net("vdd!")
    deck.process_global_net("gnd!")
    deck.osdiLoadLines.add('load "resistor.osdi"')
    deck.add_model_line("model res resistor")
    text = vacaskFormat.render_netlist(
        "// hdr\n", ["R1 ( a b ) res r=1k\n"], deck)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[0] == "// hdr"
    assert lines.index("global vdd") < lines.index("ground 0 gnd")
    assert lines.index("load \"resistor.osdi\"") < lines.index(
        "model res resistor")
    assert lines.index("model res resistor") < lines.index(
        "R1 ( a b ) res r=1k")


# ---------------------------------------------------------------------------
# records_to_ir — Qt-free end to end
# ---------------------------------------------------------------------------

def _write_symbol(lib_dir, cell):
    """A minimal res symbol with PLUS/MINUS pins 60 units apart."""
    records = [
        {"viewType": "symbol"},
        {"snapGrid": [10, 5]},
        {"type": "pin", "nam": "PLUS", "st": [0, 0], "loc": [0, 0],
         "pd": "Inout", "pt": "Signal"},
        {"type": "pin", "nam": "MINUS", "st": [60, 0], "loc": [0, 0],
         "pd": "Inout", "pt": "Signal"},
        {"type": "attr", "nam": "VacaskNetlistLine",
         "def": "@instName ( %pinOrder ) res r=@R $mfactor=@M"},
        {"type": "attr", "nam": "pinOrder", "def": "PLUS, MINUS"},
        {"type": "attr", "nam": "paramDefs",
         "def": '[{"name":"R","type":"float","default":"1k"},'
                '{"name":"M","type":"float","default":"1","min":"1f"}]'},
        {"type": "label", "nam": "@instName", "def": "[@instName]",
         "lt": "NLPLabel"},
        {"type": "label", "nam": "@R", "def": "[@R:R=%:R=1k]",
         "lt": "NLPLabel"},
        {"type": "label", "nam": "@M", "def": "[@M:M=%:M=1]",
         "lt": "NLPLabel"},
    ]
    cell_dir = lib_dir / cell
    cell_dir.mkdir(parents=True)
    (cell_dir / "symbol.json").write_text(json.dumps(records))


def _schematic_records():
    """Two-resistor divider: in -> R1 -> out -> R2 -> gnd."""
    return [
        {"viewType": "schematic"},
        {"snapGrid": [10, 5]},
        # R1 at (100,50): PLUS@(100,50) MINUS@(160,50)
        {"type": "sys", "lib": "testLib", "cell": "res", "view": "symbol",
         "nam": "R1", "ic": 1, "ld": {"R": ["1k", True], "M": ["2", True]},
         "loc": [100, 50], "ang": 0.0, "fl": [1, 1]},
        # R2 at (200,50): PLUS@(200,50) MINUS@(260,50)
        {"type": "sys", "lib": "testLib", "cell": "res", "view": "symbol",
         "nam": "R2", "ic": 2, "ld": {"R": ["1k", True]},
         "loc": [200, 50], "ang": 0.0, "fl": [1, 1]},
        {"type": "scn", "st": [0, 50], "end": [100, 50], "nam": "in",
         "ns": 3},
        {"type": "scn", "st": [160, 50], "end": [200, 50], "nam": "out",
         "ns": 3},
        {"type": "scn", "st": [260, 50], "end": [300, 50], "nam": "gnd!",
         "ns": 3},
        {"type": "scp", "st": [0, 50], "pn": "in", "pd": "Input",
         "pt": "Signal"},
    ]


def test_records_to_ir_and_format(tmp_path):
    lib_dir = tmp_path / "testLib"
    _write_symbol(lib_dir, "res")
    locator = recordsNetlist.make_pin_locator({"testLib": lib_dir})

    irs, warnings, diagnostics = recordsNetlist.records_to_ir(
        _schematic_records(), pin_locator=locator)
    assert not diagnostics
    assert [ir.name for ir in irs] == ["R1", "R2"]

    tracker = vacaskFormat._GlobalTracker()
    lines = []
    for ir in irs:
        lines.extend(vacaskFormat.format_instance_lines(
            ir, "VacaskNetlistLine", globals_tracker=tracker,
            strict_tokens=True))
    # Named wires win over the scp pin name on joined nets; R2's MINUS sits
    # on the gnd! net (processed to 'gnd').
    assert lines == [
        "R1 ( in out ) res r=1k $mfactor=2",
        "R2 ( out gnd ) res r=1k $mfactor=1",
    ]
    assert tracker.groundNets == {"gnd"}


def test_records_to_ir_missing_symbol(tmp_path):
    locator = recordsNetlist.make_pin_locator({"testLib": tmp_path})
    irs, warnings, diagnostics = recordsNetlist.records_to_ir(
        _schematic_records(), pin_locator=locator)
    # fromRecords emits a diagnostic per unresolved instance.
    assert not irs
    assert any("symbol pins not found" in d for d in diagnostics)


# ---------------------------------------------------------------------------
# Parity: interactive vacaskNetlist vs vacaskFormat on identical inputs
# ---------------------------------------------------------------------------

@pytest.fixture()
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_format_parity_with_editor_path(qapp, tmp_path):
    """format_instance_lines output equals createVacaskSymbolLine output."""
    from PySide6.QtCore import QPoint
    import revedaEditor.common.labels as lbl
    import revedaEditor.common.shapes as shp
    from revedaEditor.netlisting.vacaskNetlist import vacaskNetlist
    from revedaEditor.tests.sceneTestUtils import makeSchematicScene
    import revedaEditor.backend.libraryModelView as lmview

    libPath = tmp_path / "testLib"
    libPath.mkdir(parents=True)
    libPath.joinpath("reveda.lib").write_text("")
    model = lmview.designLibrariesModel({"testLib": libPath})
    scene = makeSchematicScene()
    editor = types.SimpleNamespace(
        centralW=types.SimpleNamespace(scene=scene),
        libraryDict={},
        libraryView=types.SimpleNamespace(libraryModel=model),
        libName="testLib", cellName="top", viewName="schematic",
        switchViewList=["schematic", "symbol"], stopViewList=["symbol"])
    netlister = vacaskNetlist(editor, tmp_path / "out.cir")

    shapes = [shp.symbolPin(QPoint(0, 0), "PLUS", "Inout", "Signal"),
              shp.symbolPin(QPoint(60, 0), "MINUS", "Inout", "Signal")]
    label_items = [
        lbl.symbolLabel(QPoint(0, 0), definition, "NLPLabel", 12,
                        "Left", "R0", "Normal")
        for definition in ("[@instName]", "[@R:R=%:1k]", "[@M:M=%:1]")]
    symbol = shp.schematicSymbol(shapes + label_items,
                                 dict(_RES_ATTRS))
    symbol.instanceName = "I1"
    for item in label_items:
        item.labelDefs()
        symbol.labels[item.labelName] = item
    # In a live scene the @instName label carries the instance name.
    symbol.labels["@instName"].labelValue = "I1"
    symbol.pinNetMap = {"PLUS": "in", "MINUS": "out"}

    editor_lines = netlister.createVacaskSymbolLine(symbol)

    ir = vacaskFormat.InstanceIR(
        name="I1",
        attrs=dict(_RES_ATTRS),
        labels={item.labelName: item.labelValue for item in label_items},
        pinNets=[("PLUS", "in"), ("MINUS", "out")])
    ir_lines, warnings = _fmt(
        ir, globals_tracker=netlister._deck.globals)

    assert ir_lines == editor_lines
    assert not warnings
