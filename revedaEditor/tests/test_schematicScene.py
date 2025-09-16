import pytest
from revedaEditor.scenes.schematicScene import schematicScene

# test_schematicScene.py

def test_isValidNetName():
    # Test case 1: Valid simple string
    assert schematicScene.isValidNetName("net1") == True

    # Test case 2: Valid bus notation
    assert schematicScene.isValidNetName("net<0:3>") == True

    # Test case 3: Invalid string with partial bus notation
    assert schematicScene.isValidNetName("net<0:>") == False

    # Test case 4: Invalid string with special characters
    assert schematicScene.isValidNetName("net<0:3") == False

    # Test case 6: Invalid string with only special characters
    assert schematicScene.isValidNetName("net<>") == False

    # Test case 7: Valid string with bus notation and extra characters
    assert schematicScene.isValidNetName("net<0:3>_extra") == False

    # Test case 8: Invalid string with incomplete bus notation
    assert schematicScene.isValidNetName("net<0:3") == False

    # Test case 9: Valid string with multiple bus notations
    assert schematicScene.isValidNetName("net<0:3><4:7>") == False

    # Test case 10: Invalid string with mixed special characters
    assert schematicScene.isValidNetName("net<0:3>:") == False

def test_matchPinToBus():
    # Test case 1: Ascending pin and net indices
    pinBaseName = "pin"
    pinIndexTuple = (0, 3)
    netBaseName = "net"
    netIndexTuple = (0, 3)
    expected_output = ([
        ("pin<0>", "net<0>"),
        ("pin<1>", "net<1>"),
        ("pin<2>", "net<2>"),
        ("pin<3>", "net<3>")
    ], 0)
    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple, 0) == expected_output

    # Test case 2: Descending pin and net indices
    pinBaseName = "pin"
    pinIndexTuple = (3, 0)
    netBaseName = "net"
    netIndexTuple = (3, 0)
    expected_output = ([
        ("pin<3>", "net<3>"),
        ("pin<2>", "net<2>"),
        ("pin<1>", "net<1>"),
        ("pin<0>", "net<0>")
    ], 0)
    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple, 0) == expected_output

    # Test case 3: Mixed pin and net indices
    pinBaseName = "pin"
    pinIndexTuple = (0, 3)
    netBaseName = "net"
    netIndexTuple = (3, 0)
    expected_output = ([
        ("pin<0>", "net<3>"),
        ("pin<1>", "net<2>"),
        ("pin<2>", "net<1>"),
        ("pin<3>", "net<0>")
    ], 0)
    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple, 0) == expected_output

    # Test case 4: Single pin and net index
    pinBaseName = "pin"
    pinIndexTuple = (1, 1)
    netBaseName = "net"
    netIndexTuple = (1, 1)
    expected_output = ([("pin<1>", "net<1>")], 0)
    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple,0) == expected_output

    # Test case 5: Single pin and net index
    pinBaseName = "pin"
    pinIndexTuple = (0, 0)
    netBaseName = "net"
    netIndexTuple = (0, 0)
    expected_output = ([("pin", "net")], 0)
    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple, 0) == expected_output

    # Test case 6: unequal pin and net indices
    pinBaseName = "pin"
    pinIndexTuple = (0, 3)
    netBaseName = "net"
    netIndexTuple = (0, 2)
    expected_output = ([
        ("pin<0>", "net<0>"),
        ("pin<1>", "net<1>"),
        ("pin<2>", "net<2>"),
        ("pin<3>", "dnet2")
    ], 3)

    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple,2) == expected_output

    # Test case 7: unequal pin and net indices with reverse orders
    pinBaseName = "pin"
    pinIndexTuple = (3,0)
    netBaseName = "net"
    netIndexTuple = (0, 2)
    expected_output = ([
        ("pin<3>", "net<0>"),
        ("pin<2>", "net<1>"),
        ("pin<1>", "net<2>"),
        ( "pin<0>", "dnet2")
    ], 3)

    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple,2) == expected_output

    # Test case 8: single net and multiple pins
    pinBaseName = "pin"
    pinIndexTuple = (0, 3)
    netBaseName = "net"
    netIndexTuple = (0, 0)
    expected_output = ([
        ("pin<0>", "net"),
        ("pin<1>", "dnet3"),
        ("pin<2>", "dnet4"),
        ("pin<3>", "dnet5")
    ], 6)

    assert schematicScene.matchPinToBus(pinBaseName, pinIndexTuple, netBaseName,
                                        netIndexTuple,3) == expected_output
if __name__ == "__main__":
    pytest.main()