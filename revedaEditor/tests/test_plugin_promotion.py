"""Fixed promotional-access policy for first-party commercial plugins."""

import sys
from datetime import datetime, timezone
from types import ModuleType

import pytest

from revedaEditor.backend import licenseManager
from revedaEditor.gui.pluginsRegistry import PluginRegistryWindow

try:
    from revedaLicense import licenseManager as licenseImpl
except ImportError:
    licenseImpl = None


BEFORE_CUTOFF = datetime(2027, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
AT_CUTOFF = datetime(2027, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
requires_private_license_source = pytest.mark.skipif(
    licenseImpl is None,
    reason="private revedaLicense source is not installed",
)


def test_fixed_promotional_window_boundaries():
    for plugin in sorted(licenseManager.PROMOTIONAL_PLUGIN_IDS):
        assert licenseManager.has_promotional_access(plugin, BEFORE_CUTOFF)
        assert not licenseManager.has_promotional_access(plugin, AT_CUTOFF)

    assert not licenseManager.has_promotional_access(
        "thirdParty", BEFORE_CUTOFF
    )


@requires_private_license_source
def test_private_module_uses_same_promotional_boundaries(monkeypatch):
    monkeypatch.setattr(licenseImpl, "has_paid_license", lambda name: False)
    for plugin in sorted(licenseManager.PROMOTIONAL_PLUGIN_IDS):
        assert licenseImpl.has_promotional_access(plugin, BEFORE_CUTOFF)
        assert not licenseImpl.has_promotional_access(plugin, AT_CUTOFF)
        assert (
            licenseImpl.get_access_info(plugin, BEFORE_CUTOFF)["source"]
            == "promotion"
        )
        assert licenseImpl.get_access_info(plugin, AT_CUTOFF)["allowed"] is False


def test_promotion_is_reported_as_access_source(monkeypatch):
    monkeypatch.setattr(licenseManager, "_compiled_get_access_info", None)
    monkeypatch.setattr(
        licenseManager, "_has_valid_paid_license", lambda name: False
    )

    info = licenseManager.get_access_info("sdl", BEFORE_CUTOFF)

    assert info["allowed"] is True
    assert info["source"] == "promotion"
    assert info["promotion_ends_at"] == "2027-04-01T00:00:00+00:00"
    assert info["days_remaining"] == 0


def test_expired_promotion_falls_back_to_prompt(monkeypatch):
    prompts = []
    monkeypatch.setattr(
        licenseManager, "_has_valid_paid_license", lambda name: False
    )
    monkeypatch.setattr(
        licenseManager, "has_promotional_access", lambda name: False
    )
    monkeypatch.setattr(
        licenseManager,
        "_prompt_for_license",
        lambda name, payment_url, parent: prompts.append(name) or False,
    )

    assert not licenseManager.check_and_prompt_license("sdl")
    assert prompts == ["sdl"]


def test_active_promotion_skips_license_prompt(monkeypatch):
    prompts = []
    monkeypatch.setattr(
        licenseManager, "_has_valid_paid_license", lambda name: False
    )
    monkeypatch.setattr(
        licenseManager, "has_promotional_access", lambda name: True
    )
    monkeypatch.setattr(
        licenseManager,
        "_prompt_for_license",
        lambda name, payment_url, parent: prompts.append(name) or False,
    )

    assert licenseManager.check_and_prompt_license("sdl")
    assert prompts == []


@requires_private_license_source
def test_private_module_prompt_short_circuits_during_promotion(monkeypatch):
    def fail_if_dialog_opens(*args, **kwargs):
        raise AssertionError("license dialog opened during promotion")

    monkeypatch.setattr(
        licenseImpl, "has_paid_license", lambda name: False
    )
    monkeypatch.setattr(
        licenseImpl, "has_promotional_access", lambda name: True
    )
    monkeypatch.setattr(licenseImpl, "LicenseDialog", fail_if_dialog_opens)

    assert licenseImpl.check_and_prompt_license("sdl")


@requires_private_license_source
def test_private_module_prompts_after_promotion(monkeypatch):
    class RejectedDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return licenseImpl.QDialog.DialogCode.Rejected

    monkeypatch.setattr(
        licenseImpl, "has_paid_license", lambda name: False
    )
    monkeypatch.setattr(
        licenseImpl, "has_promotional_access", lambda name: False
    )
    monkeypatch.setattr(licenseImpl, "LicenseDialog", RejectedDialog)

    assert not licenseImpl.check_and_prompt_license("sdl")


def test_license_module_version_gates_compatibility(
    qtbot, monkeypatch, tmp_path
):
    monkeypatch.setattr(PluginRegistryWindow, "fetch_registry", lambda self: None)
    registry = PluginRegistryWindow(plugins_dir=tmp_path / "plugins")
    qtbot.addWidget(registry)

    home = tmp_path / "home"
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    url = registry._revedaLicense_url()
    module_name = url.rsplit("/", 1)[-1]
    (home / ".reveda" / module_name).parent.mkdir(parents=True)
    (home / ".reveda" / module_name).write_bytes(b"placeholder")

    fake_package = ModuleType("revedaLicense")
    fake_impl = ModuleType("revedaLicense.licenseManager")
    fake_package.licenseManager = fake_impl
    monkeypatch.setitem(sys.modules, "revedaLicense", fake_package)
    monkeypatch.setitem(sys.modules, "revedaLicense.licenseManager", fake_impl)

    fake_impl.LICENSE_API_VERSION = 1
    assert not registry._revedaLicenseInstalled()
    fake_impl.LICENSE_API_VERSION = licenseManager.MINIMUM_LICENSE_API_VERSION
    assert registry._revedaLicenseInstalled()
