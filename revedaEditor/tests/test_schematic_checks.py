import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

import revedaEditor.checks.schematic as schk
import revedaEditor.common.net as snet
import revedaEditor.common.shapes as shp
from revedaEditor.gui import propertyDialogues as pdlg
from revedaEditor.tests.sceneTestUtils import makeSchematicScene


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(qapp):
    return makeSchematicScene()


def _runViolations(scene, ruleIds=None):
    scene.checkErrors(ruleIds)
    return scene.lastCheckViolations


def _violationsOf(violations, ruleId):
    return [v for v in violations if v.ruleId == ruleId]


def _addNet(scene, x1, y1, x2, y2):
    netItem = snet.schematicNet(QPoint(x1, y1), QPoint(x2, y2))
    scene.addItem(netItem)
    return netItem


def _addPin(scene, point, name, direction, pinType="Signal"):
    pinItem = shp.schematicPin(point, name, direction, pinType)
    scene.addItem(pinItem)
    return pinItem


def _addSymbol(scene, name, pos=None, width=40, height=20):
    rect = shp.symbolRectangle(QPoint(0, 0), QPoint(width, height))
    symbolItem = shp.schematicSymbol([rect], {})
    symbolItem.instanceName = name
    scene.addItem(symbolItem)
    symbolItem.setPos(pos if pos is not None else QPoint(0, 0))
    return symbolItem


def test_empty_scene_is_clean(scene):
    assert _runViolations(scene) == []


def test_dangling_wire_end(scene):
    _addNet(scene, 0, 0, 200, 0)
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "danglingWireEnd")) == 2
    # Both ends free: two markers. Attach a pin at one end -> one dangling.
    _addPin(scene, QPoint(0, 0), "inp", "Input")
    violations = _runViolations(scene)
    dangling = _violationsOf(violations, "danglingWireEnd")
    assert len(dangling) == 1


def test_rule_selection_skips_disabled_rules(scene):
    _addNet(scene, 0, 0, 200, 0)
    violations = _runViolations(scene, {"symbolOverlap"})
    assert violations == []
    violations = _runViolations(scene, {"danglingWireEnd"})
    assert len(violations) == 2


def test_floating_input_pin(scene):
    _addPin(scene, QPoint(300, 300), "in1", "Input")
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "floatingInputPin")) == 1
    assert _violationsOf(violations, "floatingPin") == []


def test_floating_output_pin(scene):
    _addPin(scene, QPoint(300, 300), "out1", "Output")
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "floatingPin")) == 1


def test_connected_pin_not_flagged(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addPin(scene, QPoint(0, 0), "in1", "Input")
    violations = _runViolations(scene)
    assert _violationsOf(violations, "floatingPin") == []
    assert _violationsOf(violations, "floatingInputPin") == []


def test_pin_on_wire_body_is_connected(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addPin(scene, QPoint(100, 0), "mid", "Output")
    violations = _runViolations(scene)
    assert _violationsOf(violations, "floatingPin") == []


def test_shorted_outputs(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addPin(scene, QPoint(0, 0), "o1", "Output")
    _addPin(scene, QPoint(200, 0), "o2", "Output")
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "shortedOutputs")) == 1


def test_output_and_input_not_shorted(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addPin(scene, QPoint(0, 0), "o1", "Output")
    _addPin(scene, QPoint(200, 0), "i1", "Input")
    violations = _runViolations(scene)
    assert _violationsOf(violations, "shortedOutputs") == []


def test_net_name_conflict(scene):
    netA = _addNet(scene, 0, 0, 100, 0)
    netA.name = "alpha"
    netA.nameStrength = snet.netNameStrengthEnum.SET
    netB = _addNet(scene, 100, 0, 200, 0)
    netB.name = "beta"
    netB.nameStrength = snet.netNameStrengthEnum.SET
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "netNameConflict")) == 1


def test_matching_net_names_no_conflict(scene):
    netA = _addNet(scene, 0, 0, 100, 0)
    netA.name = "alpha"
    netA.nameStrength = snet.netNameStrengthEnum.SET
    netB = _addNet(scene, 100, 0, 200, 0)
    netB.name = "alpha"
    netB.nameStrength = snet.netNameStrengthEnum.SET
    violations = _runViolations(scene)
    assert _violationsOf(violations, "netNameConflict") == []


def test_crossover_without_junction(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addNet(scene, 100, -50, 100, 50)
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "crossoverNoJunction")) == 1


def test_t_junction_not_a_crossover(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addNet(scene, 100, 0, 100, 100)  # endpoint on body = junction
    violations = _runViolations(scene)
    assert _violationsOf(violations, "crossoverNoJunction") == []


def test_overlapping_wires_flagged(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addNet(scene, 50, 0, 150, 0)  # duplicate-drawn segment, fully collinear
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "overlappingNets")) == 1


def test_parallel_offset_wires_not_flagged(scene):
    _addNet(scene, 0, 0, 200, 0)
    _addNet(scene, 0, 30, 200, 30)  # parallel but clearly separate
    violations = _runViolations(scene)
    assert _violationsOf(violations, "overlappingNets") == []


def test_duplicate_instance_names(scene):
    _addSymbol(scene, "I0", QPoint(0, 0))
    _addSymbol(scene, "I0", QPoint(300, 300))
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "duplicateInstName")) == 2


def test_symbol_overlap(scene):
    _addSymbol(scene, "I0", QPoint(0, 0))
    _addSymbol(scene, "I1", QPoint(10, 10))
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "symbolOverlap")) == 1


def test_off_grid_net_endpoint(scene):
    _addNet(scene, 3, 0, 200, 0)
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "offGridItems")) == 1


def test_bus_width_mismatch(scene):
    netItem = _addNet(scene, 0, 0, 100, 0)
    netItem.name = "a<0:7>"
    netItem.nameStrength = snet.netNameStrengthEnum.SET
    _addPin(scene, QPoint(0, 0), "a<0:3>", "Output")
    violations = _runViolations(scene)
    assert len(_violationsOf(violations, "busWidthMismatch")) == 1


def test_matching_bus_width_no_violation(scene):
    netItem = _addNet(scene, 0, 0, 100, 0)
    netItem.name = "a<0:3>"
    netItem.nameStrength = snet.netNameStrengthEnum.SET
    _addPin(scene, QPoint(0, 0), "a<0:3>", "Output")
    violations = _runViolations(scene)
    assert _violationsOf(violations, "busWidthMismatch") == []


def test_delete_errors_survives_scene_clear(scene):
    # scene.clear() deletes marker items' C++ objects; deleteErrors must
    # skip the stale references instead of crashing (regression test).
    netItem = _addNet(scene, 0, 0, 100, 0)
    netItem.name = "conflictNet"
    netItem.nameStrength = snet.netNameStrengthEnum.SET
    _addNet(scene, 0, 0, 100, 0)
    scene.checkErrors()
    assert scene.overlapRectSet
    scene.clear()
    scene.checkErrors()  # must not raise
    scene.deleteErrors()


def test_check_rules_dialogue_defaults_and_selection(qapp):
    allIds = {rule.ruleId for rule in schk.SCHEMATIC_RULES}
    dlg = pdlg.schematicCheckRulesDialogue(None, schk.SCHEMATIC_RULES, allIds)
    assert len(dlg.ruleCheckBoxes) == len(schk.SCHEMATIC_RULES)
    assert all(cb.isChecked() for cb in dlg.ruleCheckBoxes.values())
    assert dlg.selectedRuleIds() == allIds
    dlg.ruleCheckBoxes["danglingWireEnd"].setChecked(False)
    assert dlg.selectedRuleIds() == allIds - {"danglingWireEnd"}
    dlg._setAllChecked(False)
    assert dlg.selectedRuleIds() == set()
    dlg.close()


if __name__ == "__main__":
    pytest.main()
