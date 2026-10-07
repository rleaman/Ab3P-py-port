import argparse
import datetime
import json
from pathlib import Path

import bioc

def process_file(input_filename):
    abbreviations = set()
    with open(input_filename, 'r', encoding="utf-8") as fp:
        input_collection = bioc.load(fp)
    for document in input_collection.documents:
        for passage in document.passages:
            passage_abbrs = dict()
            for annotation in passage.annotations:
                if annotation.infons.get("type") != "ABBR":
                    continue
                passage_abbrs[(annotation.id, annotation.infons["ABBR"])] = annotation.text
            for relation in passage.relations:
                if relation.infons.get("type") != "ABBR":
                    continue
                # format is document.id, short form, long form
                relation_abbr = dict()
                for node in relation.nodes:
                    relation_abbr[node.role] = passage_abbrs[(node.refid, node.role)]
                abbreviations.add((document.id, relation_abbr["ShortForm"], relation_abbr["LongForm"]))
    print("Found " + str(len(abbreviations)))
    return abbreviations


def escape_tsv_field(value):
    """Escape backslashes, C0/C1 controls, and Unicode line separators.

    Fields have no surrounding quotes. JSON string escapes make the encoding
    reversible without changing printable Unicode or ordinary TSV records.
    """
    escaped = []
    for character in value:
        code = ord(character)
        if character == "\\":
            escaped.append("\\\\")
        elif code < 32 or 127 <= code <= 159 or character in "\u2028\u2029":
            escaped.append(json.dumps(character, ensure_ascii=True)[1:-1])
        else:
            escaped.append(character)
    return "".join(escaped)


def write_abbreviations(abbreviations, output_file, output_format="tsv"):
    """Write sorted, unique document/SF/LF triples, one physical line each."""
    if output_format not in ("tsv", "jsonl"):
        raise ValueError(f"Unsupported output format: {output_format}")
    for document_id, short, long in sorted(set(abbreviations)):
        if output_format == "jsonl":
            record = {"document_id": document_id, "short_form": short, "long_form": long}
            line = json.dumps(record, ensure_ascii=True)
        else:
            line = "\t".join(escape_tsv_field(field) for field in (document_id, short, long))
        output_file.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(description="Extract abbreviation pairs from BioC XML")
    parser.add_argument("input", type=Path, help="BioC XML file or directory")
    parser.add_argument("output", type=Path, help="Output file")
    parser.add_argument("--format", choices=("tsv", "jsonl"), default="tsv",
                        help="Output format (default: tsv)")
    args = parser.parse_args()

    start = datetime.datetime.now()
    input_path = args.input
    output_path = args.output
    
    abbreviations = set()
    if input_path.is_dir():
        print(f"Processing directory {input_path}")
        # Process any xml files found
        for input_filename in sorted(input_path.iterdir()):
            if input_filename.is_file() and input_filename.suffix.lower() == ".xml":
                print(f"Processing file {input_filename}")
                abbreviations.update(process_file(input_filename))
    elif input_path.is_file():
        print(f"Processing file {input_path}")
        # Process directly
        abbreviations.update(process_file(input_path))
    else:  
        raise RuntimeError(f"Path is not a directory or normal file: {input_path}")
    print("Total processing time = " + str(datetime.datetime.now() - start))

    with open(output_path, 'w', encoding="utf-8", newline="\n") as output_file:
        write_abbreviations(abbreviations, output_file, args.format)


if __name__ == "__main__":
    main()
