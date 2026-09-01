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
