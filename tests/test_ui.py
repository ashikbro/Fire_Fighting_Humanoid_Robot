import pytest

pytestmark = pytest.mark.skip(
    reason="The legacy browser tests target a removed login page; replace with API/UI tests when a login UI exists."
)

def test_legacy_login_ui_is_not_run():
    """Keep the legacy test module discoverable without requiring Selenium."""
