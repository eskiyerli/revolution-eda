from PySide6.QtCore import QPoint

from revedaEditor.common.labels import symbolLabel


class DummyParent:
    def __init__(self):
        self.cellName = "cell"
        self.instanceName = "I1"
        self.libraryName = "lib"
        self.viewName = "view"
        self.attr = {"modelName": "model"}
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
    assert result == ("bar", "bar", "foo")


def test_basic_format_without_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%]", "")
    assert result == ("?", "?", "foo")


def test_format_with_default_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%:default=abc]", "")
    assert result == ("abc", "abc", "foo")


def test_format_with_default_value_and_value():
    label = make_label()
    result = label.createNLPLabel("[@foo:%:default=abc]", "xyz")
    assert result == ("xyz", "xyz", "foo")


def test_format_without_percent():
    label = make_label()
    result = label.createNLPLabel("[@foo:bar]", "baz")
    assert result == ("bar", "baz", "foo")


def test_invalid_label_definition():
    label = make_label()
    result = label.createNLPLabel("foo", "bar")
    assert result == ("foo", "bar", "foo")


def test_predefined_label_cellName():
    label = make_label()
    result = label.createNLPLabel("[@cellName]", "")
    assert result == ("cell", "cell", "cellName")


def test_predefined_label_instName():
    label = make_label()
    result = label.createNLPLabel("[@instName]", "")
    assert result == ("I1", "I1", "instName")


def test_predefined_label_libName():
    label = make_label()
    result = label.createNLPLabel("[@libName]", "")
    assert result == ("lib", "lib", "libName")


def test_predefined_label_viewName():
    label = make_label()
    result = label.createNLPLabel("[@viewName]", "")
    assert result == ("view", "view", "viewName")


def test_predefined_label_modelName():
    label = make_label()
    result = label.createNLPLabel("[@modelName]", "")
    assert result == ("model", "model", "modelName")


def test_predefined_label_elementNum():
    label = make_label()
    result = label.createNLPLabel("[@elementNum]", "")
    assert result == ("42", "42", "elementNum")
