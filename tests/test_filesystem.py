import pytest
from pathlib import Path
from offline_toolbox.filesystem.temporary import TempFileManager, atomic_save
from offline_toolbox.filesystem.naming import generate_safe_output_path


def test_temp_manager_lifecycle(tmp_path):
    mgr = TempFileManager()
    run_dir = mgr.create_run_directory("test_")
    assert run_dir.exists()

    temp_f = mgr.create_temp_file(run_dir, ".txt")
    temp_f.write_text("temporary content")
    assert temp_f.exists()

    mgr.cleanup_run(run_dir)
    assert not run_dir.exists()


def test_atomic_save(tmp_path):
    source = tmp_path / "temp_file.txt"
    source.write_text("safe atomic data")

    target = tmp_path / "destination" / "final.txt"
    saved = atomic_save(source, target)

    assert saved == target
    assert target.exists()
    assert target.read_text() == "safe atomic data"
    assert not source.exists()


def test_generate_safe_output_path(tmp_path):
    orig = tmp_path / "report.pdf"
    orig.touch()

    # First version
    p1 = generate_safe_output_path(orig, action_suffix="compressed")
    assert p1.name == "report_compressed.pdf"

    # Simulate collision
    p1.touch()
    p2 = generate_safe_output_path(orig, action_suffix="compressed")
    assert p2.name == "report_compressed (1).pdf"
