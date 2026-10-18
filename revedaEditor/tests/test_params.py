"""Tests for the Qt-free typed parameter model (common/params.py)."""

import json
import types

import pytest
from PySide6.QtCore import QPoint

import revedaEditor.common.params as prm


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def defsJson(*defs):
    return json.dumps(list(defs))


def _makeInstance(qapp, symattrs=None, labelDefs=()):
    """A schematicSymbol instance with the given symattrs + NLP labels."""
    import revedaEditor.common.labels as lbl
    import revedaEditor.common.shapes as shp
    labelItems = [lbl.symbolLabel(QPoint(0, 0), definition, "NLPLabel", 12,
                                  "Left", "R0", "Normal")
                  for definition in labelDefs]
    symbolItem = shp.schematicSymbol(labelItems, symattrs or {})
    symbolItem.instanceName = "I0"
    for labelItem in labelItems:
        labelItem.labelDefs()
        symbolItem.labels[labelItem.labelName] = labelItem
    return symbolItem


class TestParse:
    def test_empty(self):
        assert prm.paramDefsFromJson("") == ([], [])
        assert prm.paramDefsFromSymattrs({}) == []
        assert prm.paramDefsFromSymattrs(None) == []

    def test_roundtrip(self):
        defs = [
            prm.ParamDef("r", "float", default="1k", minimum="1",
                         maximum="1G", parse=True),
            prm.ParamDef("mode", "choice", default="lin",
                         choices=("lin", "log")),
            prm.ParamDef("flag", "boolean", default="true",
                         display=False),
            prm.ParamDef("note", "string", parse=False),
        ]
        parsed, errors = prm.paramDefsFromJson(prm.paramDefsToJson(defs))
        assert errors == []
        assert parsed == defs

    def test_symattrs(self):
        symattrs = {prm.PARAMDEFS_ATTR: defsJson(
            {"name": "w", "type": "float", "default": "1u"})}
        defs = prm.paramDefsFromSymattrs(symattrs)
        assert len(defs) == 1
        assert defs[0].name == "w" and defs[0].default == "1u"

    def test_malformed_json(self):
        defs, errors = prm.paramDefsFromJson("{not json")
        assert defs == [] and errors

    def test_non_list(self):
        defs, errors = prm.paramDefsFromJson('{"name": "r"}')
        assert defs == [] and errors

    def test_missing_name_skipped(self):
        defs, errors = prm.paramDefsFromJson(
            defsJson({"type": "float"}, {"name": "r"}))
        assert [d.name for d in defs] == ["r"]
        assert any("name" in e for e in errors)

    def test_unknown_type_becomes_string(self):
        defs, errors = prm.paramDefsFromJson(
            defsJson({"name": "x", "type": "complex"}))
        assert defs[0].type == "string" and errors

    def test_choices_csv(self):
        defs, _ = prm.paramDefsFromJson(
            defsJson({"name": "m", "type": "choice",
                      "choices": "a, b ,c"}))
        assert defs[0].choices == ("a", "b", "c")

    def test_validate_param_defs(self):
        defs, errors = prm.paramDefsFromJson(defsJson(
            {"name": "r", "type": "float", "min": "10", "max": "1"},
            {"name": "r", "type": "float"},
            {"name": "c", "type": "choice"}))
        messages = " ".join(errors)
        assert "Duplicate" in messages
        assert "no choices" in messages
        assert "min 10 > max 1" in messages


class TestValidation:
    def test_float_quantiphy(self):
        pd = prm.ParamDef("r", "float")
        assert prm.validateValue(pd, "1k") == []
        assert prm.validateValue(pd, "2.5u") == []
        assert prm.validateValue(pd, "abc")

    def test_float_no_parse(self):
        pd = prm.ParamDef("r", "float", parse=False)
        assert prm.validateValue(pd, "2.5") == []
        assert prm.validateValue(pd, "1k")  # suffix rejected when parse off

    def test_int(self):
        pd = prm.ParamDef("n", "int")
        assert prm.validateValue(pd, "4") == []
        assert prm.validateValue(pd, "4.5")
        assert prm.validateValue(pd, "x")

    def test_range(self):
        pd = prm.ParamDef("w", "float", minimum="100n", maximum="10u")
        assert prm.validateValue(pd, "1u") == []
        assert prm.validateValue(pd, "10n")
        assert prm.validateValue(pd, "100u")

    def test_boolean(self):
        pd = prm.ParamDef("flag", "boolean")
        for good in ("true", "False", "1", "0", "yes", "off"):
            assert prm.validateValue(pd, good) == []
        assert prm.validateValue(pd, "maybe")
        assert prm.normalizeValue(pd, "Yes") == "true"
        assert prm.normalizeValue(pd, "0") == "false"

    def test_choice(self):
        pd = prm.ParamDef("corner", "choice", choices=("tt", "ff", "ss"))
        assert prm.validateValue(pd, "ff") == []
        assert prm.validateValue(pd, "xx")

    def test_string(self):
        pd = prm.ParamDef("note", "string")
        assert prm.validateValue(pd, "anything at all") == []

    def test_empty_is_valid(self):
        pd = prm.ParamDef("r", "float", minimum="1")
        assert prm.validateValue(pd, "") == []

    def test_deferred_expression(self):
        """Whole-value ``{expr}`` is deferred to the simulator (parametric
        sweeps), so it bypasses local type and range checks."""
        pd = prm.ParamDef("dc", "float", minimum="0", maximum="5")
        assert prm.validateValue(pd, "{dcin}") == []
        assert prm.validateValue(pd, "{2*vdd}") == []
        assert prm.validateValue(pd, "{}")  # empty braces are not deferred
        assert prm.validateValue(prm.ParamDef("n", "int"), "{n}") == []
        assert prm.validateValue(
            prm.ParamDef("c", "choice", choices=("tt", "ff")),
            "{corner}") == []
        assert prm.validateValue(
            prm.ParamDef("f", "boolean"), "{flag}") == []

    def test_deferred_default(self):
        defs, errors = prm.paramDefsFromJson(defsJson(
            {"name": "dc", "type": "float", "default": "{dcin}"}))
        assert errors == []
        assert prm.effectiveValue(defs[0], "") == "{dcin}"

    def test_value_with_ppar(self):
        pd = prm.ParamDef("l", "float")
        assert prm.validateValue(pd, 'pPar("w")',
                               {"w": "1u"}) == []
        assert prm.validateValue(pd, 'pPar("w")', {"w": "abc"})


class TestPPar:
    def test_resolve_default(self):
        pd = prm.ParamDef("l", "float", default='pPar("w")')
        assert prm.resolveDefault(pd, {"w": "2u"}) == "2u"

    def test_at_prefixed_sibling(self):
        pd = prm.ParamDef("l", "float", default='pPar("w")')
        assert prm.resolveDefault(pd, {"@w": "2u"}) == "2u"

    def test_list_valued_sibling(self):
        pd = prm.ParamDef("l", "float", default='pPar("w")')
        # sys.ld record shape: name -> [value, visible]
        assert prm.resolveDefault(pd, {"@w": ["2u", True]}) == "2u"

    def test_unresolved_stays_literal(self):
        pd = prm.ParamDef("l", "float", default='pPar("w")')
        assert prm.resolveDefault(pd, {}) == 'pPar("w")'

    def test_chain(self):
        pd = prm.ParamDef("a", "float", default='pPar("b")')
        assert prm.resolveDefault(pd, {"b": 'pPar("c")',
                                       "c": "5"}) == "5"

    def test_cycle_terminates(self):
        pd = prm.ParamDef("a", "float", default='pPar("b")')
        out = prm.resolveDefault(pd, {"b": 'pPar("a")',
                                      "a": 'pPar("b")'})
        assert isinstance(out, str)  # terminates, stays literal

    def test_embedded_refs(self):
        pd = prm.ParamDef("a", "string",
                          default='pPar("w")*pPar("l")')
        assert prm.resolveDefault(pd, {"w": "2", "l": "3"}) == "2*3"


class TestEffectiveValue:
    def test_explicit_value_wins(self):
        pd = prm.ParamDef("r", "float", default="1k")
        assert prm.effectiveValue(pd, "2k") == "2k"

    def test_default_applies(self):
        pd = prm.ParamDef("r", "float", default="1k")
        assert prm.effectiveValue(pd, "") == "1k"
        assert prm.effectiveValue(pd, "  ") == "1k"

    def test_apply_defaults(self):
        defs = [prm.ParamDef("r", "float", default="1k"),
                prm.ParamDef("l", "float", default='pPar("w")'),
                prm.ParamDef("n", "int")]
        out = prm.applyDefaults(defs, {"@w": "5u"})
        assert out == {"@r": "1k", "@l": "5u"}


class TestInstanceValidation:
    def test_validate_ld_records(self):
        defs = [prm.ParamDef("r", "float"),
                prm.ParamDef("n", "int", maximum="8")]
        errors = prm.validateInstanceValues(
            defs, {"@r": ["abc", True], "@n": ["20", True]}, owner="I1")
        assert any("'r'" in e and "I1" in e for e in errors)
        assert any("'n'" in e for e in errors)

    def test_missing_values_skipped(self):
        defs = [prm.ParamDef("r", "float")]
        assert prm.validateInstanceValues(defs, {}) == []


class TestInferType:
    @pytest.mark.parametrize("value,expected", [
        ("1k", "float"), ("2.5u", "float"), ("4", "int"),
        ("0", "int"), ("true", "boolean"), ("off", "boolean"),
        ("name", "string"), ("{dcin}", "float"),
    ])
    def test_infer(self, value, expected):
        assert prm.inferType(value) == expected


# --- integration: symbol instance labels -------------------------------------


class TestInstanceIntegration:
    def test_paramDefs_property(self, qapp):
        inst = _makeInstance(qapp, symattrs={
            prm.PARAMDEFS_ATTR: defsJson({"name": "r", "type": "float"})})
        assert [pd.name for pd in inst.paramDefs] == ["r"]

    def test_paramdefs_empty(self, qapp):
        inst = _makeInstance(qapp, symattrs={"pinOrder": "a,b"})
        assert inst.paramDefs == []

    def test_paramdef_default_overrides_nlp(self, qapp):
        """paramDef.default wins over the NLP literal default when the
        instance value is empty."""
        inst = _makeInstance(
            qapp,
            symattrs={prm.PARAMDEFS_ATTR: defsJson(
                {"name": "r", "type": "float", "default": "2k"})},
            labelDefs=("[@instName]", "[@r:r=%:1k]"))
        assert inst.labels["@r"].labelValue == "2k"

    def test_explicit_value_beats_paramdef_default(self, qapp):
        inst = _makeInstance(
            qapp,
            symattrs={prm.PARAMDEFS_ATTR: defsJson(
                {"name": "r", "type": "float", "default": "2k"})},
            labelDefs=("[@instName]", "[@r:r=%:1k]"))
        inst.labels["@r"].labelValue = "4.7k"
        inst.labels["@r"].labelDefs()
        assert inst.labels["@r"].labelValue == "4.7k"

    def test_ppar_default_resolves_sibling(self, qapp):
        inst = _makeInstance(
            qapp,
            symattrs={prm.PARAMDEFS_ATTR: defsJson(
                {"name": "w", "type": "float", "default": "1u"},
                {"name": "l", "type": "float", "default": 'pPar("w")'})},
            labelDefs=("[@instName]", "[@w:w=%:3u]", "[@l:l=%:500n]"))
        # w's value comes from its paramDef default, l inherits via pPar.
        assert inst.labels["@w"].labelValue == "1u"
        assert inst.labels["@l"].labelValue == "1u"

    def test_pending_params_applied(self, qapp):
        """_applyPendingInstanceParams writes place-form values onto the
        placed instance's labels."""
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene
        scene = makeSchematicScene()
        inst = _makeInstance(
            qapp,
            symattrs={prm.PARAMDEFS_ATTR: defsJson(
                {"name": "r", "type": "float", "default": "1k"})},
            labelDefs=("[@instName]", "[@r:r=%:1k]"))
        scene.pendingInstanceParams = {"r": "9.1k"}
        scene._applyPendingInstanceParams(inst)
        assert inst.labels["@r"].labelValue == "9.1k"


# --- integration: record-level diagnostics -----------------------------------


class TestDiagnostics:
    def _locator(self, paramDefs):
        def locator(lib, cell, view):
            return {"in": (0, 0), "out": (60, 0),
                    "directions": {}, "paramDefs": paramDefs}
        return locator

    def test_param_value_error(self):
        from revedaEditor.connectivity.diagnostics import checkRecords
        defs = [prm.ParamDef("r", "float")]
        records = [{"viewType": "schematic"}, {},
                   {"type": "sys", "lib": "L", "cell": "res",
                    "view": "symbol", "nam": "I1", "loc": [0, 0],
                    "ld": {"@r": ["abc", True]}}]
        _result, diags = checkRecords(records,
                                      pinLocator=self._locator(defs))
        assert any(d.kind == "paramValueError" and "I1" in d.message
                   for d in diags)

    def test_valid_params_clean(self):
        from revedaEditor.connectivity.diagnostics import checkRecords
        defs = [prm.ParamDef("r", "float")]
        records = [{"viewType": "schematic"}, {},
                   {"type": "sys", "lib": "L", "cell": "res",
                    "view": "symbol", "nam": "I1", "loc": [0, 0],
                    "ld": {"@r": ["1k", True]}}]
        _result, diags = checkRecords(records,
                                      pinLocator=self._locator(defs))
        assert not any(d.kind == "paramValueError" for d in diags)

    def test_no_locator_no_param_diags(self):
        from revedaEditor.connectivity.diagnostics import checkRecords
        records = [{"viewType": "schematic"}, {},
                   {"type": "sys", "lib": "L", "cell": "res",
                    "view": "symbol", "nam": "I1", "loc": [0, 0],
                    "ld": {"@r": ["abc", True]}}]
        _result, diags = checkRecords(records)
        assert not any(d.kind == "paramValueError" for d in diags)

    def test_locator_metadata_keys_not_treated_as_pins(self):
        """pinMap metadata (directions, paramDefs) must not be read as pin
        positions — regression: 'Malformed sys record: list index out of
        range' on every instance."""
        from revedaEditor.connectivity.adapters import fromRecords
        from revedaEditor.connectivity.diagnostics import checkRecords
        defs = [prm.ParamDef("r", "float")]
        records = [{"viewType": "schematic"}, {},
                   {"type": "sys", "lib": "L", "cell": "res",
                    "view": "symbol", "nam": "I1", "loc": [10, 20],
                    "ld": {"@r": ["1k", True]}}]
        _result, diags = checkRecords(records,
                                      pinLocator=self._locator(defs))
        assert not any(d.kind in ("malformedRecord", "unresolvedInstance")
                       for d in diags)
        # Two real pins produced, at loc + pin offset.
        _segs, ports, adapterDiags = fromRecords(
            records, pinLocator=self._locator(defs))
        assert adapterDiags == []
        assert sorted(p.point for p in ports) == [(10.0, 20.0),
                                                  (70.0, 20.0)]


# --- integration: dialogs ------------------------------------------------------


class TestDialogs:
    def test_param_value_widget_types(self, qapp):
        from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit
        from revedaEditor.gui.propertyDialogues import paramValueWidget
        w, get, _set = paramValueWidget(
            prm.ParamDef("b", "boolean", default="true"), "false")
        assert isinstance(w, QCheckBox) and get() == "false"
        _set("true")
        assert get() == "true"
        w, get, _ = paramValueWidget(
            prm.ParamDef("c", "choice", choices=("a", "b")), "b")
        assert isinstance(w, QComboBox) and get() == "b"
        w, get, _ = paramValueWidget(prm.ParamDef("r", "float"), "1k")
        assert isinstance(w, QLineEdit) and get() == "1k"

    def test_place_instance_dialog_values(self, qapp):
        from revedaEditor.gui.propertyDialogues import placeInstanceDialog
        defs = [prm.ParamDef("r", "float", default="1k"),
                prm.ParamDef("hidden", "string", default="x",
                             display=False)]
        dlg = placeInstanceDialog(None, defs)
        # Hidden params are not on the form.
        assert [p.name for p, _ in dlg.paramRows] == ["r"]
        assert dlg.paramValues() == {"r": "1k"}

    def test_place_dialog_hidden_sibling_ppar_paramdef_ctor(
            self, qapp, monkeypatch):
        """Legacy ParamDef-only constructor resolves a visible pPar default
        against a display=False sibling without rendering it."""
        from PySide6.QtWidgets import QDialog, QMessageBox
        from revedaEditor.gui.propertyDialogues import placeInstanceDialog
        defs = [
            prm.ParamDef("w", "float", default="2u", display=False),
            prm.ParamDef("l", "float", default='pPar("w")'),
        ]
        dlg = placeInstanceDialog(None, defs)
        assert [p.name for p, _ in dlg.paramRows] == ["l"]
        assert {row["labelName"] for row in dlg.labelRows} == {"@l"}
        assert dlg.paramValues() == {"l": "2u"}
        assert dlg._validationContext["@w"] == "2u"
        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            lambda *a, **k: warnings.append(a))
        dlg._validateAndAccept()
        assert warnings == []
        assert dlg.result() == QDialog.DialogCode.Accepted

    def test_place_dialog_rejects_invalid(self, qapp):
        from revedaEditor.gui.propertyDialogues import placeInstanceDialog
        defs = [prm.ParamDef("r", "float", default="1k")]
        dlg = placeInstanceDialog(None, defs)
        _pdef, getValue = dlg.paramRows[0]
        widget = dlg.findChild(type(dlg.paramRows[0]) and __import__(
            "PySide6.QtWidgets", fromlist=["QLineEdit"]).QLineEdit)
        widget.setText("not-a-number")
        # _validateAndAccept shows a warning instead of accepting; with
        # offscreen Qt it must not raise and dialog stays non-accepted.
        assert prm.validateValue(defs[0], getValue()) != []

    def test_instance_dialog_typed_rows(self, qapp):
        """Rows remain label-driven while ParamDefs select typed widgets."""
        from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit
        from revedaEditor.gui.propertyDialogues import instanceProperties
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene
        scene = makeSchematicScene()
        inst = _makeInstance(
            qapp,
            symattrs={prm.PARAMDEFS_ATTR: defsJson(
                {"name": "r", "type": "float", "default": "1k"},
                {"name": "flag", "type": "boolean", "default": "true"},
                {"name": "mode", "type": "choice",
                 "choices": ["a", "b"], "default": "a"},
                {"name": "secret", "type": "string", "default": "s",
                 "display": False})},
            labelDefs=("[@instName]", "[@r:r=%:1k]", "[@flag:flag=%:true]",
                       "[@mode:mode=%:a]", "[@secret:s=%:x]",
                       "[@note:note=%:hi]"))
        dlg = instanceProperties(None)
        scene._buildInstanceLabelRows(dlg, inst)
        rowsByName = {row["labelName"]: row for row in dlg.labelRows}
        # display=False ParamDef rows stay off the rendered form; apply
        # carries their values over from the original instance.
        assert "@secret" not in rowsByName
        assert "@secret" in dlg.hiddenLabelNames
        assert "@note" in rowsByName
        assert isinstance(rowsByName["@r"]["valueEdit"], QLineEdit)
        assert isinstance(rowsByName["@flag"]["valueEdit"], QCheckBox)
        assert isinstance(rowsByName["@mode"]["valueEdit"], QComboBox)
        assert isinstance(rowsByName["@note"]["valueEdit"], QLineEdit)
        assert rowsByName["@note"]["paramDef"] is None
        # Boolean read-back normalizes through getValue.
        assert rowsByName["@flag"]["getValue"]() == "true"

    def test_place_dialog_hidden_sibling_context(self, qapp, monkeypatch):
        """A visible pPar value resolves against a hidden bound row that is
        never rendered on the placement form."""
        from PySide6.QtWidgets import QDialog, QMessageBox
        from revedaEditor.gui.propertyDialogues import placeInstanceDialog
        lDef = prm.ParamDef("l", "float")
        wDef = prm.ParamDef("w", "float", display=False)
        rows = [
            {"labelName": "@l", "value": 'pPar("w")', "paramDef": lDef,
             "isEditable": True, "isVisible": True},
            {"labelName": "@w", "value": "2u", "paramDef": wDef,
             "isEditable": False, "isVisible": False},
        ]
        dlg = placeInstanceDialog(None, rows)
        rendered = {row["labelName"] for row in dlg.labelRows}
        assert "@w" not in rendered and "@l" in rendered
        assert dlg._validationContext["@w"] == "2u"
        assert dlg.paramValues() == {"@l": 'pPar("w")'}
        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            lambda *a, **k: warnings.append(a))
        dlg._validateAndAccept()
        assert warnings == []
        assert dlg.result() == QDialog.DialogCode.Accepted

    def test_configure_schematic_instance_params(self, qapp, monkeypatch):
        """_configureSchematicInstanceParams wires refreshPreview and stores
        the accepted values as pending placement params."""
        from PySide6.QtWidgets import QDialog
        import revedaEditor.backend.dataDefinitions as ddef
        import revedaEditor.gui.propertyDialogues as pdlg
        import revedaEditor.gui.schematicEditor as sched
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene

        scene = makeSchematicScene()
        scene.newInstanceTuple = ddef.viewNameTuple("lib", "cell", "symbol")
        scene.pendingInstanceParams = None
        scene.pendingInstanceArraySpec = None
        monkeypatch.setattr(
            scene, "instSymbol",
            lambda _tuple, _pos, allocateName=True: _makeInstance(
                qapp,
                symattrs={prm.PARAMDEFS_ATTR: defsJson(
                    {"name": "r", "type": "float", "default": "1k"})},
                labelDefs=("[@instName]", "[@r:r=%:1k]")))

        class _FakeDialog:
            def __init__(self, *args, **kwargs):
                self.labelRows = []
                self._onValuesChanged = kwargs.get("onValuesChanged")

            def refreshPreview(self):
                if self._onValuesChanged is not None:
                    self._onValuesChanged(self.paramValues())

            def paramValues(self):
                return {"r": "7.5k"}

            def arraySpec(self):
                return None

            def exec(self):
                return QDialog.DialogCode.Accepted

        monkeypatch.setattr(pdlg, "placeInstanceDialog", _FakeDialog)
        editor = types.SimpleNamespace(
            centralW=types.SimpleNamespace(scene=scene),
            messageLine=types.SimpleNamespace(setText=lambda *a: None),
            logger=scene.logger)
        assert sched.schematicEditor._configureSchematicInstanceParams(editor)
        assert scene.pendingInstanceParams == {"r": "7.5k"}

    def test_symbol_labels_dialogue_params_table(self, qapp):
        from revedaEditor.fileio.symbolEncoder import symbolAttribute
        from revedaEditor.gui.propertyDialogues import symbolLabelsDialogue
        attrs = [symbolAttribute("pinOrder", "a,b"),
                 symbolAttribute(prm.PARAMDEFS_ATTR, defsJson(
                     {"name": "r", "type": "float", "default": "1k"}))]
        dlg = symbolLabelsDialogue(None, [], attrs)
        # Reserved attr excluded from the free-form attribute table.
        assert all(name != prm.PARAMDEFS_ATTR
                   for name, _ in dlg.symbolAttributes())
        defs = dlg.paramDefs()
        assert len(defs) == 1 and defs[0].name == "r" \
               and defs[0].default == "1k"


# --- integration: instance properties dialog ---------------------------------


class _Stub:
    """Minimal stand-in for QLineEdit/QComboBox text accessors."""

    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value

    def currentText(self):
        return self._value


def _dialogFor(item, rows, hidden=(), lib="lib", cell="cell"):
    return types.SimpleNamespace(
        libNameEdit=_Stub(lib), cellNameEdit=_Stub(cell),
        viewNameEdit=_Stub("symbol"), instNameEdit=_Stub("I0"),
        angleEdit=_Stub("0"), netSetEdit=_Stub(""),
        labelRows=rows, hiddenLabelNames=list(hidden))


def _valueRow(labelName, value, pdef=None):
    return {"labelName": labelName, "isPyLabel": False, "paramDef": pdef,
            "getValue": lambda: value, "setValue": lambda v: None,
            "visibleCombo": _Stub("True")}


def _patchInstSymbol(monkeypatch, scene, qapp, symattrs, labelDefs):
    monkeypatch.setattr(
        scene, "instSymbol",
        lambda vt, loc: _makeInstance(
            qapp, symattrs=symattrs, labelDefs=labelDefs))


class TestBuildInstanceFromDialog:
    SYM = {"p": None}
    LABEL_DEFS = ("[@instName]", "[@w:w=%:1u]", "[@secret:s=%:2u]")

    def _symattrs(self):
        return {prm.PARAMDEFS_ATTR: defsJson(
            {"name": "w", "type": "float"},
            {"name": "secret", "type": "float", "display": False})}

    def test_hidden_param_preserved(self, qapp, monkeypatch):
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene
        scene = makeSchematicScene()
        symattrs = self._symattrs()
        original = _makeInstance(qapp, symattrs=symattrs,
                                 labelDefs=self.LABEL_DEFS)
        original.labels["@w"].labelValue = "3u"
        original.labels["@secret"].labelValue = "9u"
        wDef = next(p for p in original.paramDefs if p.name == "w")
        dlg = _dialogFor(original, [_valueRow("@w", "5u", wDef)],
                         hidden=("@secret",))
        _patchInstSymbol(monkeypatch, scene, qapp, symattrs,
                         self.LABEL_DEFS)
        newInst = scene._buildInstanceFromDialog(dlg, original, QPoint(0, 0))
        assert newInst.labels["@w"].labelValue == "5u"
        assert newInst.labels["@secret"].labelValue == "9u"

    def test_invalid_value_falls_back_to_original(self, qapp, monkeypatch):
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene
        scene = makeSchematicScene()
        symattrs = self._symattrs()
        original = _makeInstance(qapp, symattrs=symattrs,
                                 labelDefs=self.LABEL_DEFS)
        original.labels["@w"].labelValue = "3u"
        wDef = next(p for p in original.paramDefs if p.name == "w")
        dlg = _dialogFor(original, [_valueRow("@w", "abc", wDef)])
        _patchInstSymbol(monkeypatch, scene, qapp, symattrs,
                         self.LABEL_DEFS)
        newInst = scene._buildInstanceFromDialog(dlg, original, QPoint(0, 0))
        # 'abc' fails float validation -> keeps the original 3u, not the
        # symbol default 1u.
        assert newInst.labels["@w"].labelValue == "3u"

    def test_valid_value_normalizes(self, qapp, monkeypatch):
        from revedaEditor.tests.sceneTestUtils import makeSchematicScene
        scene = makeSchematicScene()
        symattrs = self._symattrs()
        original = _makeInstance(qapp, symattrs=symattrs,
                                 labelDefs=self.LABEL_DEFS)
        wDef = next(p for p in original.paramDefs if p.name == "w")
        dlg = _dialogFor(original, [_valueRow("@w", " 4.7u ", wDef)])
        _patchInstSymbol(monkeypatch, scene, qapp, symattrs,
                         self.LABEL_DEFS)
        newInst = scene._buildInstanceFromDialog(dlg, original, QPoint(0, 0))
        assert newInst.labels["@w"].labelValue == "4.7u"
