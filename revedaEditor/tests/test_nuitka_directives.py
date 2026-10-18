"""Packaging regression tests: Nuitka build directives embedded in reveda.py."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVEDA_PY = REPO_ROOT / "reveda.py"


def test_freelist_disable_directive_present():
    """Nuitka 4.3 corrupts free_list_frames on Python 3.13/3.14, causing
    delayed SIGSEGVs in _MAKE_COMPILED_FRAME. The standalone build must keep
    --experimental=disable-freelist-all until an upstream fix is verified."""
    source = REVEDA_PY.read_text(encoding="utf-8")
    assert "# nuitka-project: --experimental=disable-freelist-all" in source
