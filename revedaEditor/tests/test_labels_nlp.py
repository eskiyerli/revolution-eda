from PySide6.QtCore import QPoint

from revedaEditor.common.labels import symbolLabel


class DummyParent:
    def __init__(self):
        self.cellName = "cell"
        self.instanceName = "I1"
        self.libraryName = "lib"
        self.viewName = "view"
        self.symattrs = {"modelName": "model"}
        self.counter = 42
        self.labels = {}


def make_label():
    label = symbolLabel(QPoint(0, 0), "[@testLabel:%]", "NLPLabel", 10, "Left",
                        "R0", "Normal")
    label.parentItem = lambda: DummyParent()
    return label


def test_basic_format_with_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%]", "bar")
    assert result == ("@foo", "bar", "bar")


def test_basic_format_without_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%]", "")
    assert result == ("@foo", "", "")


def test_format_with_default_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%:default=abc]", "")
    assert result == ("@foo", "abc", "abc")


def test_format_with_default_value_and_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%:default=abc]", "xyz")
    assert result == ("@foo", "xyz", "xyz")


def test_format_without_percent():
    label = make_label()
    result = label.createNLPLabel("[@foo:bar]", "baz")
    assert result == ("@foo", "bar", "baz")


def test_invalid_label_definition():
    label = make_label()
    result = label.createNLPLabel("foo", "bar")
    assert result == ("", "", "")


def test_predefined_label_cellName():
    label = make_label()
    result = label.createNLPLabel("[@cellName]", "")
    assert result == ("@cellName", "cell", "cell")


def test_predefined_label_instName():
    label = make_label()
    result = label.createNLPLabel("[@instName]", "")
    assert result == ("@instName", "I1", "I1")


def test_predefined_label_libName():
    label = make_label()
    result = label.createNLPLabel("[@libName]", "")
    assert result == ("@libName", "lib", "lib")


def test_predefined_label_viewName():
    label = make_label()
    result = label.createNLPLabel("[@viewName]", "")
    assert result == ("@viewName", "view", "view")


def test_predefined_label_modelName():
    label = make_label()
    result = label.createNLPLabel("[@modelName]", "")
    assert result == ("@modelName", "model", "model")


def test_predefined_label_elementNum():
    label = make_label()
    result = label.createNLPLabel("[@elementNum]", "")
    assert result == ("@elementNum", "42", "42")
