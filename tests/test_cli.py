import shutil
import sys

from ab3p.__main__ import main


def test_directory_input_and_output(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    shutil.copy("examples/input/collection_000001_tiab.xml", input_dir / "one.xml")
    shutil.copy("examples/input/collection_000002_tiab.xml", input_dir / "two.XML")
    (input_dir / "ignored.txt").write_text("not XML")

    monkeypatch.setattr(sys, "argv", ["ab3p", str(input_dir), str(output_dir)])
    main()

    assert sorted(path.name for path in output_dir.iterdir()) == ["one.xml", "two.XML"]
    assert all(path.stat().st_size > 0 for path in output_dir.iterdir())
    assert "\n  <document>" in (output_dir / "one.xml").read_text(encoding="utf-8")
