import argparse
from pathlib import Path

from .bioc import annotate_file


def main():
    parser = argparse.ArgumentParser(description="Identify abbreviations in BioC XML")
    parser.add_argument("input", help="input BioC collection or directory of XML files")
    parser.add_argument("output", help="output BioC collection or directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.is_dir():
        if output_path.exists() and not output_path.is_dir():
            parser.error("output must be a directory when input is a directory")
        output_path.mkdir(parents=True, exist_ok=True)

        xml_files = sorted(
            path for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() == ".xml"
        )
        for xml_file in xml_files:
            annotate_file(xml_file, output_path / xml_file.name)
        return

    if not input_path.is_file():
        parser.error(f"input does not exist or is not a file: {input_path}")

    if output_path.is_dir():
        output_path = output_path / input_path.name
    annotate_file(input_path, output_path)


if __name__ == "__main__":
    main()
