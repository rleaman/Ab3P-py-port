import json
import sys

from src import extract_abbreviations


def test_jsonl_output_escapes_control_characters(tmp_path, monkeypatch):
    input_path = tmp_path / "input.xml"
    output_path = tmp_path / "output.jsonl"
    input_path.touch()
    pair = ("doc\n1", "short\t\x00\x7f", "long\r\n\x1f\x85\u2028")
    monkeypatch.setattr(extract_abbreviations, "process_file", lambda path: {pair})
    monkeypatch.setattr(sys, "argv", ["extract_abbreviations.py", str(input_path),
                                    str(output_path), "--format", "jsonl"])

    extract_abbreviations.main()

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == dict(zip(
        ("document_id", "short_form", "long_form"), pair
    ))
    assert all(ord(character) >= 32 for character in lines[0])
    assert "\x7f" not in lines[0]
    assert "\\n" in lines[0]
    assert "\\t" in lines[0]
    assert "\\u0000" in lines[0]
    assert "\\u007f" in lines[0]
    assert "\\u0085" in lines[0]


def test_tsv_remains_default(tmp_path, monkeypatch):
    input_path = tmp_path / "input.xml"
    output_path = tmp_path / "output.tsv"
    input_path.touch()
    monkeypatch.setattr(extract_abbreviations, "process_file", lambda path: {("doc", "SF", "LF")})
    monkeypatch.setattr(sys, "argv", ["extract_abbreviations.py", str(input_path),
                                    str(output_path)])

    extract_abbreviations.main()

    assert output_path.read_text(encoding="utf-8") == "doc\tSF\tLF\n"
