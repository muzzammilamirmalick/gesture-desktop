import pytest

import paths


@pytest.fixture(autouse=True)
def user_files_in_a_temp_folder(tmp_path, monkeypatch):
    """Tests never read or write your real saved gestures or settings."""
    monkeypatch.setattr(paths, "user_file", lambda name: tmp_path / name)
