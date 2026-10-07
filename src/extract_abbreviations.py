import argparse
import datetime
import json
import os
from pathlib import Path

import bioc

def process_file(input_filename):
    abbreviations = set()
    with open(input_filename, 'r') as fp:
        input_collection = bioc.load(fp)
    for document in input_collection.documents:
        passage_abbrs = dict()
        for passage in document.passages:
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
    start = datetime.datetime.now()
    if os.path.isdir(input_path):
        print(f"Processing directory {input_path}")
        # Process any xml files found
        dir = os.listdir(input_path)
        for item in dir:
            input_filename = input_path / item
            if os.path.isfile(input_filename) and input_filename.suffix.lower() == ".xml":
                print(f"Processing file {input_filename}")
                abbreviations.update(process_file(input_filename))
    elif os.path.isfile(input_path):
        print(f"Processing file {input_path}")
        # Process directly
        abbreviations.update(process_file(input_path))
    else:  
        raise RuntimeError(f"Path is not a directory or normal file: {input_path}")
    print("Total processing time = " + str(datetime.datetime.now() - start))

    abbreviations = list(abbreviations)
    abbreviations.sort()

    with open(output_path, 'w', encoding="utf-8", newline="\n") as output_file:
        for document_id, short, long in abbreviations:
            if args.format == "jsonl":
                record = {
                    "document_id": document_id,
                    "short_form": short,
                    "long_form": long,
                }
                # ensure_ascii also escapes non-ASCII control characters.
                line = json.dumps(record, ensure_ascii=True).replace("\x7f", "\\u007f")
            else:
                line = f"{document_id}\t{short}\t{long}"
            output_file.write(line + "\n")


if __name__ == "__main__":
    main()
