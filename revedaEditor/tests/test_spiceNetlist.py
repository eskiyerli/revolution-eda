from revedaEditor.fileio.spiceNetlist import parse_extracted_netlist


def test_parse_klayout_pin_comments_into_named_extracted_nets(tmp_path):
    netlist_path = tmp_path / "comSourceAmp_extracted.cir"
    netlist_path.write_text(
        """* Extracted by KLayout

* cell comSourceAmp
* pin DRAIN
* pin GATE
* pin SOURCE
.SUBCKT comSourceAmp 2 1 4
* net 1 GATE
* net 2 DRAIN
* net 4 SOURCE
M$1 2 1 4 3 sg13_lv_nmos L=0.13u W=6u
.ENDS comSourceAmp
""",
        encoding="utf-8",
    )

    extracted = parse_extracted_netlist(netlist_path, "comSourceAmp")

    assert extracted["pins"] == ["DRAIN", "GATE", "SOURCE"]
    assert extracted["devices"][0]["terminals"] == {
        "D": "DRAIN",
        "G": "GATE",
        "S": "SOURCE",
        "B": "3",
    }
    assert {net["name"] for net in extracted["nets"]} == {
        "3",
        "DRAIN",
        "GATE",
        "SOURCE",
    }


def test_parse_use_net_names_true(tmp_path):
    """When no_net_names=false (use_net_names=true), KLayout writes net names
    directly in the .SUBCKT and device lines and does NOT emit * net comments.
    The parser must use the net names from the .SUBCKT line, not fall back to
    the pin names from * pin comments.
    """
    netlist_path = tmp_path / "comSourceAmp_extracted.cir"
    netlist_path.write_text(
        """* Extracted by KLayout

* cell comSourceAmp
* pin DRAIN
* pin GATE
* pin SOURCE
.SUBCKT comSourceAmp DRAIN GATE SOURCE
M$1 DRAIN GATE SOURCE 3 sg13_lv_nmos L=0.13u W=6u
.ENDS comSourceAmp
""",
        encoding="utf-8",
    )

    extracted = parse_extracted_netlist(netlist_path, "comSourceAmp")

    # Pins must be the net names from the .SUBCKT line, not the pin names
    # from * pin comments (they happen to match here, but the logic is tested).
    assert extracted["pins"] == ["DRAIN", "GATE", "SOURCE"]
    assert extracted["devices"][0]["terminals"] == {
        "D": "DRAIN",
        "G": "GATE",
        "S": "SOURCE",
        "B": "3",
    }
    assert {net["name"] for net in extracted["nets"]} == {
        "3",
        "DRAIN",
        "GATE",
        "SOURCE",
    }


def test_parse_use_net_names_true_pin_name_differs_from_net_name(tmp_path):
    """When the pin name differs from the net name connected to it, the
    parser must use the net name (from .SUBCKT line), not the pin name
    (from * pin comments).  This is the core bug: KLayout's .SUBCKT line
    uses net_to_string(net_for_pin), not the pin name itself.
    """
    netlist_path = tmp_path / "amp_extracted.cir"
    netlist_path.write_text(
        """* Extracted by KLayout

* cell amp
* pin IN
* pin OUT
* pin VDD
* pin VSS
.SUBCKT amp in out vdd vss
M$1 out in 4 vss sg13_lv_nmos L=0.13u W=6u
M$2 out 5 vdd vdd sg13_lv_pmos L=0.13u W=6u
.ENDS amp
""",
        encoding="utf-8",
    )

    extracted = parse_extracted_netlist(netlist_path, "amp")

    # Pins must be net names from .SUBCKT, NOT pin names from * pin comments
    assert extracted["pins"] == ["in", "out", "vdd", "vss"]
    assert extracted["devices"][0]["terminals"] == {
        "D": "out",
        "G": "in",
        "S": "4",
        "B": "vss",
    }
    assert extracted["devices"][1]["terminals"] == {
        "D": "out",
        "G": "5",
        "S": "vdd",
        "B": "vdd",
    }
    # Nets must not contain pin names (IN, OUT, VDD, VSS) as separate entries
    assert {net["name"] for net in extracted["nets"]} == {
        "4",
        "5",
        "in",
        "out",
        "vdd",
        "vss",
    }
