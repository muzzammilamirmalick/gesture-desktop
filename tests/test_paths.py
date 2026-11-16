"""Where files live when run with Python and when packaged."""

import sys
from pathlib import Path

import paths


def test_with_python_everything_is_in_the_project_folder():
    assert paths.resource("models/x.task") == paths.APP_FOLDER / "models/x.task"
    assert paths.user_folder() == paths.APP_FOLDER


def test_packaged_models_come_from_the_unpack_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.resource("models/x.task") == tmp_path / "models/x.task"


def test_packaged_saves_go_to_the_user_account(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    folder = paths.user_folder()
    assert folder != paths.APP_FOLDER
    assert str(folder).startswith(str(tmp_path))
    assert folder.name in (paths.APP_NAME, ".gesture-control")
