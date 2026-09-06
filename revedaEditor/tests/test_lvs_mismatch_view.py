from revedaEditor.backend.LVSModelView import (
    LVSDeviceParamMismatchTableModel,
    LVSTerminalMismatchTableModel,
    LVSNetMismatchTableModel,
    LVSMissingItemTableModel,
)


def test_device_param_mismatch_table_model():
    rows = [
        {
            "layout_dev": "M$1",
            "schem_dev": "M0",
            "device_type": "sg13_lv_nmos",
            "param_name": "W",
            "layout_val_str": "1.0 µm",
            "schem_val_str": "4.0 µm",
            "delta_str": "-3.0 µm (-75.0%)",
            "status": "❌ Mismatch",
        },
        {
            "layout_dev": "M$1",
            "schem_dev": "M0",
            "device_type": "sg13_lv_nmos",
            "param_name": "L",
            "layout_val_str": "0.13 µm",
            "schem_val_str": "0.13 µm",
            "delta_str": "0",
            "status": "✓ Match",
        },
    ]
    model = LVSDeviceParamMismatchTableModel(rows)
    assert model.rowCount() == 2
    assert model.columnCount() == 8
    assert model.data(model.index(0, 0)) == "M$1"
    assert model.data(model.index(0, 3)) == "W"
    assert model.data(model.index(0, 7)) == "❌ Mismatch"
    assert model.data(model.index(1, 7)) == "✓ Match"


def test_terminal_mismatch_table_model():
    rows = [
        {
            "device_name": "M$1 ↔ M0",
            "terminal": "D",
            "layout_net": "DRAIN",
            "schem_net": "DRAIN",
            "status": "✓ Match",
        },
        {
            "device_name": "M$1 ↔ M0",
            "terminal": "B",
            "layout_net": "3",
            "schem_net": "VSS",
            "status": "❌ Mismatch",
        },
    ]
    model = LVSTerminalMismatchTableModel(rows)
    assert model.rowCount() == 2
    assert model.columnCount() == 5
    assert model.data(model.index(0, 1)) == "D"
    assert model.data(model.index(0, 4)) == "✓ Match"
    assert model.data(model.index(1, 4)) == "❌ Mismatch"


def test_net_mismatch_table_model():
    rows = [
        {
            "item_type": "Net",
            "layout_ref": "GATE",
            "schem_ref": "GATE",
            "status": "✓ Match",
            "details": "Equivalent",
        },
        {
            "item_type": "Net",
            "layout_ref": "3",
            "schem_ref": "VSS",
            "status": "❌ Mismatch",
            "details": "Status code: 0",
        },
    ]
    model = LVSNetMismatchTableModel(rows)
    assert model.rowCount() == 2
    assert model.columnCount() == 5
    assert model.data(model.index(0, 0)) == "Net"
    assert model.data(model.index(1, 3)) == "❌ Mismatch"


def test_missing_item_table_model():
    rows = [
        {
            "category": "Device",
            "name": "M0",
            "type": "sg13_lv_nmos",
            "details": "W=4.0 µm, L=0.13 µm, ng=4",
            "terminals": "D: OUT, G: IN, S: VSS, B: VSS",
            "status": "❌ Missing in Layout",
        },
        {
            "category": "Net",
            "name": "VDD",
            "type": "Schematic Net",
            "details": "Connected: M1.D, M2.S",
            "terminals": "-",
            "status": "❌ Missing in Layout",
        },
    ]
    model = LVSMissingItemTableModel(rows)
    assert model.rowCount() == 2
    assert model.columnCount() == 6
    assert model.data(model.index(0, 0)) == "Device"
    assert model.data(model.index(0, 1)) == "M0"
    assert model.data(model.index(0, 5)) == "❌ Missing in Layout"
    assert model.data(model.index(1, 0)) == "Net"
    assert model.data(model.index(1, 1)) == "VDD"

