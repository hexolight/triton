import pytest


@pytest.fixture(autouse=True)
def isolated_app_data(tmp_path, monkeypatch):
    """Keep staging/bin folders inside the test's tmp dir, never the real user profile."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
