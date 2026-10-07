import json
import sys
from io import StringIO

import pytest
from lxml import etree

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


CONTROL_TEXT = ("".join(chr(i) for i in range(32))
                + "".join(chr(i) for i in range(127, 160)) + "\u2028\u2029")


@pytest.mark.parametrize("output_format", ["tsv", "jsonl"])
@pytest.mark.parametrize("field_index", [0, 1, 2])
def test_all_controls_round_trip_in_each_field(output_format, field_index):
    pair = ["doc", "SF", "LF"]
    pair[field_index] = CONTROL_TEXT + ' literal \\n \\t \\u0000 "quote" \\ \u03b1 \U0001f9ec'
    stream = StringIO()
    extract_abbreviations.write_abbreviations([tuple(pair)], stream, output_format)
    serialized = stream.getvalue()
    assert serialized.endswith("\n")
    assert len(serialized.splitlines()) == 1
    line = serialized[:-1]
    if output_format == "tsv":
        fields = line.split("\t")
        assert len(fields) == 3
        decoded = [json.loads('"' + field.replace('"', '\\"') + '"') for field in fields]
        payload = "".join(fields)
    else:
        record = json.loads(line)
        decoded = [record[name] for name in ("document_id", "short_form", "long_form")]
        payload = line
    assert decoded == pair
    assert not any(character in payload for character in CONTROL_TEXT)


@pytest.mark.parametrize("output_format", ["tsv", "jsonl"])
def test_output_records_are_sorted_unique_and_separate(output_format):
    pairs = [("z", "SF", "LF"), ("a", "S\nF", "L\tF"), ("z", "SF", "LF")]
    stream = StringIO()
    extract_abbreviations.write_abbreviations(pairs, stream, output_format)
    lines = stream.getvalue().splitlines()
    assert len(lines) == 2
    if output_format == "jsonl":
        assert [json.loads(line)["document_id"] for line in lines] == ["a", "z"]
    else:
        assert lines == ["a\tS\\nF\tL\\tF", "z\tSF\tLF"]


@pytest.mark.parametrize("output_format", ["tsv", "jsonl"])
def test_cli_reads_utf8_xml_and_escapes_output(tmp_path, monkeypatch, output_format):
    pair = ("doc\t1", "S\nF", '\u03b1 long\r\nform\\literal "quoted"')
    collection = etree.Element("collection")
    doc = etree.SubElement(collection, "document")
    etree.SubElement(doc, "id").text = pair[0]
    passage = etree.SubElement(doc, "passage")
    etree.SubElement(passage, "offset").text = "0"
    for aid, role, value in [("SF0", "ShortForm", pair[1]), ("LF0", "LongForm", pair[2])]:
        annotation = etree.SubElement(passage, "annotation", id=aid)
        etree.SubElement(annotation, "infon", key="type").text = "ABBR"
        etree.SubElement(annotation, "infon", key="ABBR").text = role
        etree.SubElement(annotation, "location", offset="0", length=str(len(value)))
        etree.SubElement(annotation, "text").text = value
    relation = etree.SubElement(passage, "relation", id="R0")
    etree.SubElement(relation, "infon", key="type").text = "ABBR"
    etree.SubElement(relation, "node", refid="SF0", role="ShortForm")
    etree.SubElement(relation, "node", refid="LF0", role="LongForm")
    source = tmp_path / "input.xml"
    output = tmp_path / f"output.{output_format}"
    etree.ElementTree(collection).write(str(source), encoding="utf-8")
    assert extract_abbreviations.process_file(source) == {pair}
    monkeypatch.setattr(sys, "argv", ["extract_abbreviations.py", str(source), str(output),
                                     "--format", output_format])
    extract_abbreviations.main()
    raw = output.read_bytes()
    assert raw.count(b"\n") == 1
    assert b"\r" not in raw
    line = raw.decode("utf-8")[:-1]
    if output_format == "jsonl":
        assert json.loads(line) == dict(zip(("document_id", "short_form", "long_form"), pair))
    else:
        assert [json.loads('"' + field.replace('"', '\\"') + '"')
                for field in line.split("\t")] == list(pair)


def test_tsv_preserves_printable_unicode_and_escapes_literal_backslashes():
    stream = StringIO()
    extract_abbreviations.write_abbreviations([("doc", '\u03b1"', r"literal\n")], stream)
    assert stream.getvalue() == 'doc\t\u03b1"\tliteral\\\\n\n'
