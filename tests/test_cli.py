import sys

from lxml import etree
import pytest

from ab3p.__main__ import main


def test_directory_input_and_output(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    source = ("<collection><source>test</source><document><id>one</id><passage>"
              "<offset>0</offset><text>central nervous system (CNS)</text>"
              "</passage></document></collection>")
    (input_dir / "one.xml").write_text(source, encoding="utf-8")
    (input_dir / "two.XML").write_text(source, encoding="utf-8")
    (input_dir / "ignored.txt").write_text("not XML")

    monkeypatch.setattr(sys, "argv", ["ab3p", str(input_dir), str(output_dir)])
    main()

    assert sorted(path.name for path in output_dir.iterdir()) == ["one.xml", "two.XML"]
    assert all(path.stat().st_size > 0 for path in output_dir.iterdir())
    assert "\n  <document>" in (output_dir / "one.xml").read_text(encoding="utf-8")
    for path in output_dir.iterdir():
        tree = etree.parse(str(path))
        assert len(tree.findall(".//relation")) == 1
        assert tree.findall(".//annotation/text")[1].text == "CNS"


@pytest.mark.parametrize("cutoff", ["-1", "1.01", "nan"])
def test_cli_rejects_invalid_precision_cutoff(monkeypatch, cutoff):
    monkeypatch.setattr(sys, "argv", ["ab3p", "input.xml", "output.xml", "--min-precision", cutoff])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_cli_explicit_cutoff(tmp_path, monkeypatch):
    source = tmp_path / "input.xml"
    output = tmp_path / "output.xml"
    source.write_text("<collection><document><id>one</id><passage><offset>0</offset>"
                      "<text>channel1 (C1)</text>"
                      "</passage></document></collection>", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["ab3p", str(source), str(output)])
    main()
    assert len(etree.parse(str(output)).findall(".//relation")) == 1
    monkeypatch.setattr(sys, "argv", ["ab3p", str(source), str(output), "--min-precision", "0.9"])
    main()
    assert not etree.parse(str(output)).findall(".//relation")
