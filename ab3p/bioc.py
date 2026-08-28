"""BioC XML adapter for the Ab3P command-line application."""

from copy import deepcopy
from datetime import date
from lxml import etree


def _child(parent, name):
    return parent.find(name)


def annotate_file(input_name, output_name, detector=None):
    from .algorithm import Ab3P
    detector = detector or Ab3P()
    tree = etree.parse(str(input_name), etree.XMLParser(remove_blank_text=True, huge_tree=True))
    root = tree.getroot()
    out = etree.Element(root.tag, nsmap=root.nsmap)
    # The C++ connector writes a fresh collection header and changes the key.
    for child in root:
        if child.tag in ("date", "key"):
            continue
        if child.tag == "document":
            continue
        out.append(deepcopy(child))
    date_node = etree.SubElement(out, "date")
    date_node.text = date.today().strftime("%Y%m%d")
    key_node = etree.SubElement(out, "key")
    key_node.text = "abbreviation.key"

    lf_id = sf_id = rel_id = 0
    for document in root.findall("document"):
        new_doc = etree.SubElement(out, "document")
        for child in document:
            if child.tag != "passage":
                new_doc.append(deepcopy(child))
                continue
            passage = etree.SubElement(new_doc, "passage")
            text_node = child.find("text")
            text = text_node.text if text_node is not None and text_node.text else ""
            for item in child:
                if item.tag not in ("text", "annotation", "relation"):
                    passage.append(deepcopy(item))
            offset_node = child.find("offset")
            passage_offset = int(offset_node.text or 0) if offset_node is not None else 0
            for item in detector.find(text, passage_offset):
                lf = etree.SubElement(passage, "annotation", id=f"LF{lf_id}")
                lf_id += 1
                etree.SubElement(lf, "infon", key="ABBR").text = "LongForm"
                etree.SubElement(lf, "infon", key="type").text = "ABBR"
                etree.SubElement(lf, "location", offset=str(item.lf_offset), length=str(len(item.lf)))
                etree.SubElement(lf, "text").text = item.lf
                sf = etree.SubElement(passage, "annotation", id=f"SF{sf_id}")
                sf_id += 1
                etree.SubElement(sf, "infon", key="ABBR").text = "ShortForm"
                etree.SubElement(sf, "infon", key="type").text = "ABBR"
                etree.SubElement(sf, "location", offset=str(item.sf_offset), length=str(len(item.sf)))
                etree.SubElement(sf, "text").text = item.sf
                rel = etree.SubElement(passage, "relation", id=f"R{rel_id}")
                rel_id += 1
                etree.SubElement(rel, "infon", key="type").text = "ABBR"
                etree.SubElement(rel, "node", refid=lf.get("id"), role="LongForm")
                etree.SubElement(rel, "node", refid=sf.get("id"), role="ShortForm")
    etree.ElementTree(out).write(
        str(output_name),
        encoding="UTF-8",
        xml_declaration=True,
        doctype='<!DOCTYPE collection SYSTEM "BioC.dtd">',
        pretty_print=True,
    )
