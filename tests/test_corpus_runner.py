"""Runner tests use fabricated XML only; these are not C++ reference evidence."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import pytest

from corpus.make_challenge import CASES, generate
from corpus.runner.run_reference import execute
from corpus.runner import run_reference
from corpus.runner.validate_bundle import validate_output_doc
from corpus import prepare
from corpus import package as corpus_package
from corpus.enrich_metadata import article_metadata
from corpus import family_index
import gzip
import tarfile
import json


def test_challenge_passages_round_trip(tmp_path):
    (tmp_path / "manifests").mkdir()
    rows, intents = generate(tmp_path)
    docs = ET.parse(tmp_path / "input/challenge/challenge_00001.xml").getroot().findall("document")
    assert len(rows) == len(intents) == len(docs)
    assert len(rows) >= 17
    root_repo = Path(__file__).resolve().parents[1]
    table = root_repo / "BioC_C++_1.1/BioC-APPL-ABBR/WordData/Ab3P_prec.dat"
    strategies = {line.split()[2] for line in table.read_text(encoding="ascii").splitlines()
                  if len(line.split()) >= 4}
    assert len(strategies) == 17
    assert strategies <= {case[0] for case in CASES}
    for row, doc in zip(rows, docs):
        passages = doc.findall("passage")
        assert len(passages) >= 2
        assert int(passages[1].findtext("offset")) == len(passages[0].findtext("text")) + 1
        assert row["document_id"] == doc.findtext("id")


def test_xml_forbidden_control_is_not_a_bioc_fixture():
    root = ET.Element("text")
    root.text = "alpha\x01beta"
    with pytest.raises(ET.ParseError):
        ET.fromstring(ET.tostring(root, encoding="utf-8"))


def test_carriage_return_is_preserved_as_decoded_passage_text():
    root = ET.Element("collection")
    doc = ET.SubElement(root, "document")
    passage = ET.SubElement(doc, "passage")
    ET.SubElement(passage, "text").text = "alpha\rbeta"
    serialized = prepare.xml_bytes(root)
    assert b"&#13;" in serialized
    assert ET.fromstring(serialized).findtext(".//text") == "alpha\rbeta"


def test_pubmed_metadata_for_coverage_and_family_links():
    article = ET.fromstring(
        "<PubmedArticle><MedlineCitation><PMID>7</PMID><Article>"
        "<Journal><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue>"
        "<Title>Test Journal</Title></Journal><PublicationTypeList>"
        "<PublicationType>Journal Article</PublicationType></PublicationTypeList>"
        "</Article><MeshHeadingList><MeshHeading><DescriptorName>Cells</DescriptorName>"
        "</MeshHeading></MeshHeadingList></MedlineCitation><PubmedData><ArticleIdList>"
        "<ArticleId IdType='doi'>10.1234/ABC</ArticleId>"
        "<ArticleId IdType='pmc'>PMC8</ArticleId></ArticleIdList>"
        "<ReferenceList><Reference><ArticleIdList>"
        "<ArticleId IdType='doi'>10.9999/WRONG</ArticleId>"
        "<ArticleId IdType='pmc'>PMC999</ArticleId>"
        "</ArticleIdList></Reference></ReferenceList>"
        "</PubmedData></PubmedArticle>")
    record = article_metadata(article)
    assert record["pub_year"] == "2020"
    assert record["article_types"] == ["Journal Article"]
    assert record["subjects"] == ["Cells"]
    assert record["doi"] == "10.1234/abc"
    assert record["pmcid"] == "PMC8"


def test_pmc_cross_reference_keeps_multiple_linked_ids(tmp_path, monkeypatch):
    path = tmp_path / "links.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as out:
        out.write("DOI,PMCID,PMID\n10.1/A,PMC8,7\n10.1/B,PMC9,7\n")
    monkeypatch.setattr(family_index, "download", lambda: path)
    assert len(family_index.links_for({"7"})["7"]) == 2
    assert family_index.links_for_pmcids({"PMC9"})["PMC9"][0]["pmid"] == "7"


def test_cached_bioc_batch_maps_requested_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(prepare, "CACHE", tmp_path)
    protocol = {"seed": "test", "frames": {"pubmed": {"id_range_inclusive": [1, 100]}},
                "batching": {"pubmed": {"start_ordinal": 0, "size": 2}}}
    ids = [prepare.candidate("pubmed", n, protocol) for n in (0, 1)]
    xml = ("<?xml version='1.0'?><collection><source>test</source>"
           + "".join(f"<document><id>{n}</id><passage><infon key='type'>title</infon>"
                     f"<offset>0</offset><text>Title {n}</text></passage></document>" for n in ids)
           + "</collection>").encode()
    batch = tmp_path / "batches/pubmed/000000000.xml"
    batch.parent.mkdir(parents=True)
    batch.write_bytes(xml)
    memory = {}
    first, _, provenance = prepare.fetch_sample("pubmed", ids[0], 0, protocol, 0, [0], memory)
    second, _, _ = prepare.fetch_sample("pubmed", ids[1], 1, protocol, 0, [0], memory)
    assert ET.fromstring(first).findall("document")[0].findtext("id") == str(ids[0])
    assert ET.fromstring(second).findall("document")[0].findtext("id") == str(ids[1])
    assert provenance["raw_batch_sha256"] == prepare.digest(xml)
    assert prepare.raw_path("pubmed", ids[0]).is_file()


def test_cached_bioc_batch_reports_identical_duplicate_document(tmp_path, monkeypatch):
    monkeypatch.setattr(prepare, "CACHE", tmp_path)
    protocol = {"seed": "test", "frames": {"pmc": {"id_range_inclusive": [1, 100]}},
                "batching": {"pmc": {"start_ordinal": 0, "size": 2}}}
    ident = prepare.candidate("pmc", 0, protocol)
    document = f"<document><id>{ident}</id><passage><offset>0</offset><text>same</text></passage></document>"
    batch = tmp_path / "batches/pmc/000000000.xml"
    batch.parent.mkdir(parents=True)
    batch.write_text("<?xml version='1.0'?><collection>" + document * 2 + "</collection>", encoding="utf-8")
    data, _, provenance = prepare.fetch_sample("pmc", ident, 0, protocol, 0, [0], {})
    assert ET.fromstring(data).findall("document")[0].findtext("id") == str(ident)
    assert provenance["duplicate_returned_ids"] == [ident]
    batch.write_text("<?xml version='1.0'?><collection>" + document
                     + document.replace("same", "different") + "</collection>", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Conflicting duplicate"):
        prepare.fetch_sample("pmc", ident, 0, protocol, 0, [0], {})


def test_fake_runner_success_and_truncated_xml(tmp_path, monkeypatch):
    app = tmp_path / "app with spaces"
    app.mkdir()
    (app / "abbr").write_bytes(b"fake executable")
    inp = tmp_path / "input with spaces.xml"
    inp.write_text("<collection><document><id>D1</id><passage><offset>0</offset>"
                   "<text>alpha beta (AB)</text></passage></document></collection>", encoding="utf-8")
    output = b"<collection><document><id>D1</id><passage><offset>0</offset></passage></document></collection>"
    expected = [{"document_id": "D1", "passages": [{"canonical_offset": 0}]}]
    assert run_reference.parse_output(b"\xff", expected)[1].startswith("invalid_utf8:")
    calls = []

    def fake_run(command, cwd, stdout, stderr, timeout, check):
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0, output, b"diagnostic")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = tmp_path / "reference/output.xml"
    err = tmp_path / "reference/stderr.txt"
    log = tmp_path / "reference/runs.jsonl"
    good, reason, _ = execute(app, inp, out, err, 30, log, "input.xml", None, "fake", expected)
    assert good and reason == "exit_0"
    assert out.read_bytes() == output
    assert list(err.parent.glob("stderr.*.txt"))[0].read_bytes() == b"diagnostic"
    assert calls[0][1] == app
    assert str(inp.resolve()) in calls[0][0]
    assert validate_output_doc(ET.parse(inp).getroot().find("document"),
                               ET.fromstring(output).find("document")) == []

    def truncated(command, cwd, stdout, stderr, timeout, check):
        return subprocess.CompletedProcess(command, 0, b"<collection><document>", b"bad")

    monkeypatch.setattr(subprocess, "run", truncated)
    bad, reason, _ = execute(app, inp, out, err, 30, log, "input.xml", None, "fake", expected)
    assert not bad and reason.startswith("invalid_xml")
    assert out.read_bytes() == output
    assert list(out.parent.glob("output.xml.*.failed"))


def test_reference_span_and_relation_validation():
    source = ET.fromstring("<document><id>D</id><passage><offset>10</offset>"
                           "<text>β alpha</text></passage></document>")
    valid = ET.fromstring(
        "<document><id>D</id><passage><offset>10</offset>"
        "<text>\u03b2 alpha</text>"
        "<annotation id='LF1'><infon key='ABBR'>LongForm</infon>"
        "<location offset='10' length='2'/><text>β</text></annotation>"
        "<annotation id='SF1'><infon key='ABBR'>ShortForm</infon>"
        "<location offset='13' length='5'/><text>alpha</text></annotation>"
        "<relation id='R1'><node refid='LF1' role='LongForm'/>"
        "<node refid='SF1' role='ShortForm'/></relation>"
        "</passage></document>")
    assert validate_output_doc(source, valid) == []
    valid.find("passage/text").text = "changed"
    assert "passage_text" in validate_output_doc(source, valid)
    valid.find("passage/text").text = "\u03b2 alpha"
    valid.find(".//node[@role='ShortForm']").set("refid", "missing")
    assert "relation_refid" in validate_output_doc(source, valid)
    valid.find(".//annotation[@id='LF1']/location").set("length", "1")
    assert "annotation_span" in validate_output_doc(source, valid)


def test_supplied_ascii_reference_is_structurally_valid():
    root = Path(__file__).resolve().parents[1]
    source = ET.parse(root / "examples/input/collection_tiab_00001.xml").getroot().findall("document")
    reference = ET.parse(root / "examples/reference_output/collection_tiab_00001.xml").getroot().findall("document")
    assert len(source) == len(reference) == 200
    assert all(not validate_output_doc(original, annotated)
               for original, annotated in zip(source, reference))


def test_fake_shard_crash_isolates_and_recovers_documents(tmp_path, monkeypatch):
    corpus = tmp_path / "bundle with spaces"
    app = tmp_path / "app with spaces"
    app.mkdir()
    (app / "abbr").write_bytes(b"fake executable")
    inp = corpus / "input/development/pubmed_tiab_00001.xml"
    inp.parent.mkdir(parents=True)
    root = ET.Element("collection")
    for tag, value in (("source", "test"), ("date", "20261007"), ("key", "test.key")):
        ET.SubElement(root, tag).text = value
    for docid in ("D1", "D2"):
        doc = ET.SubElement(root, "document")
        ET.SubElement(doc, "id").text = docid
        passage = ET.SubElement(doc, "passage")
        ET.SubElement(passage, "offset").text = "0"
        ET.SubElement(passage, "text").text = "alpha beta"
    inp.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    filehash = run_reference.file_sha(inp)
    rows = [{"file": "input/development/pubmed_tiab_00001.xml", "index": i,
             "document_id": docid, "partition": "development", "cohort": "pubmed",
             "file_sha256": filehash, "passages": [{"canonical_offset": 0}]}
            for i, docid in enumerate(("D1", "D2"))]
    manifests = corpus / "manifests"
    manifests.mkdir()
    (manifests / "inputs.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def fake_run(command, cwd, stdout, stderr, timeout, check):
        source = ET.parse(command[1]).getroot()
        docs = source.findall("document")
        if len(docs) > 1:
            return subprocess.CompletedProcess(command, 1, b"<collection>", b"simulated crash")
        output = ET.Element("collection")
        doc = ET.SubElement(output, "document")
        ET.SubElement(doc, "id").text = docs[0].findtext("id")
        passage = ET.SubElement(doc, "passage")
        ET.SubElement(passage, "offset").text = "0"
        return subprocess.CompletedProcess(command, 0, ET.tostring(output, encoding="utf-8"), b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["run_reference.py", "--corpus", str(corpus),
                                     "--abbr-app", str(app), "--retries", "0"])
    run_reference.main()
    terminal = [json.loads(line) for line in (corpus / "reference_cpp/documents.jsonl").read_text().splitlines()]
    attempts = [json.loads(line) for line in (corpus / "reference_cpp/runs.jsonl").read_text().splitlines()]
    assert len(terminal) == 2
    assert all(row["status"] == "success" and row["output_path"].startswith("reference_cpp/recovered/")
               for row in terminal)
    assert len(attempts) == 3
    assert [row["status"] for row in attempts] == ["failed", "success", "success"]


def test_canonical_build_preserves_unicode_and_removes_annotations(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    bundle = tmp_path / "representative_v1"
    monkeypatch.setattr(prepare, "CACHE", cache)
    monkeypatch.setattr(prepare, "BUNDLE", bundle)
    protocol = {
        "protocol_version": "test",
        "allocation": [{"partition": part, "pubmed": int(part == "development"),
                        "pmc": int(part == "development")}
                       for part in ("development", "holdout", "reserve")],
        "shards": {"pubmed_documents": 100, "pmc_documents": 20},
        "frames": {"pubmed": {"id_range_inclusive": [1, 100]},
                   "pmc": {"id_range_inclusive": [1, 100]}},
        "sources": {"pubmed": "https://example.org/{id}", "pmc": "https://example.org/{id}"},
    }
    selected = []
    for cohort, ident, docid in (("pubmed", 7, "7"), ("pmc", 8, "PMC8")):
        root = ET.Element("collection")
        doc = ET.SubElement(root, "document")
        ET.SubElement(doc, "id").text = docid
        if cohort == "pmc":
            ET.SubElement(doc, "infon", key="license").text = "CC BY"
        for typ, value, offset in (("title", "β title", 90),
                                   ("abstract" if cohort == "pubmed" else "body", "🧬 alpha beta", 500)):
            passage = ET.SubElement(doc, "passage")
            ET.SubElement(passage, "infon", key="type").text = typ
            ET.SubElement(passage, "offset").text = str(offset)
            ET.SubElement(passage, "text").text = value
            ET.SubElement(passage, "annotation", id="old")
        raw = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        path = prepare.raw_path(cohort, ident)
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        selected.append({"status": "selected", "cohort": cohort, "partition": "development",
                         "id": ident, "ordinal": 0,
                         "raw_sha256": prepare.digest(raw), "raw_bytes": len(raw),
                         "identifiers": {"pmid" if cohort == "pubmed" else "pmcid": docid},
                         "license": "CC BY" if cohort == "pmc" else "",
                         "year": "2020", "publisher": None,
                         "passage_types": ["title", "abstract" if cohort == "pubmed" else "body"]})
    prepare.append_log(cache / "selection.jsonl", selected[0])
    prepare.append_log(cache / "selection.jsonl", selected[1])
    prepare.build(protocol)
    for file in (bundle / "input/development").glob("*.xml"):
        doc = ET.parse(file).getroot().find("document")
        passages = doc.findall("passage")
        assert passages[0].findtext("text") == "β title"
        assert passages[1].findtext("text") == "🧬 alpha beta"
        assert passages[0].findtext("offset") == "0"
        assert passages[1].findtext("offset") == str(len("β title") + 1)
        assert not doc.findall(".//annotation")
    inputs = [json.loads(line) for line in (bundle / "manifests/inputs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(inputs) == 2
    assert inputs[0]["passages"][0]["source_offset"] == "90"

    # Exercise the real packaging and relocated-input validation path on a
    # tiny synthetic fixture. No fixture output is stored in the real bundle.
    (bundle / "protocol.json").write_text(json.dumps(protocol), encoding="utf-8")
    for name in ("metadata.jsonl", "metadata_requests.jsonl", "pmc_links.jsonl"):
        (bundle / "manifests" / name).write_text("", encoding="utf-8")
    names = ("articles.jsonl", "metadata.jsonl", "metadata_requests.jsonl", "pmc_links.jsonl")
    (bundle / "manifests/metadata_complete.json").write_text(json.dumps({
        "articles": 2, "sha256": {name: prepare.digest((bundle / "manifests" / name).read_bytes())
                                  for name in names}}), encoding="utf-8")
    (cache / "metadata").mkdir(exist_ok=True)
    (cache / "metadata/selected_family_links.jsonl").write_text("", encoding="utf-8")
    (cache / "metadata/PMC-ids.csv.json").write_text("{}", encoding="utf-8")
    (cache / "metadata/excluded_family_keys.json").write_text("{\"keys\":[]}", encoding="utf-8")
    monkeypatch.setattr(corpus_package, "BUNDLE", bundle)
    monkeypatch.setattr(corpus_package, "CACHE", cache)
    monkeypatch.setattr(corpus_package, "sanity_rows", lambda _: [])
    corpus_package.main()
    archive = tmp_path / "representative_v1.input.tar.gz"
    assert archive.is_file()
    assert (tmp_path / "representative_v1.input.tar.gz.sha256").is_file()
    with tarfile.open(archive, "r:gz") as tar:
        assert {member.name.split("/")[0] for member in tar.getmembers()} == {"representative_v1"}
        assert not any("cache" in member.name or "mock" in member.name for member in tar.getmembers())
