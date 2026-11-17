"""Conservative DOCX extraction for researcher-reviewed ASR references.

No speaker labels, headings, fillers or dialect words are discarded automatically.
Paragraphs and table cells are kept in document XML order. User must review text
before approving it for scoring. The original DOCX is read-only.
"""
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


@dataclass(frozen=True)
class GroundTruthDraft:
    source_path: str
    text: str
    blocks: tuple[str, ...]
    warning: str


def extract_docx(path: str) -> GroundTruthDraft:
    original = Path(path)
    if not original.is_file() or original.suffix.lower() != ".docx":
        raise ValueError("Choose an existing .docx document")
    if original.name.startswith("~$"):
        raise ValueError("Temporary Word lock files cannot be references")
    doc = Document(str(original))
    blocks = []
    seen_paragraphs = set()
    # Iterate Word body elements in document order, unlike separate paragraphs/tables.
    for element in doc.element.body.iterchildren():
        if element.tag == qn("w:p"):
            value = "".join(node.text or "" for node in element.iter(qn("w:t"))).strip()
            if value:
                blocks.append(value)
        elif element.tag == qn("w:tbl"):
            for row in element.findall(qn("w:tr")):
                for cell in row.findall(qn("w:tc")):
                    # A cell may contain several paragraphs; don't duplicate merged cells.
                    for para in cell.iter(qn("w:p")):
                        if id(para) in seen_paragraphs:
                            continue
                        seen_paragraphs.add(id(para))
                        value = "".join(node.text or "" for node in para.iter(qn("w:t"))).strip()
                        if value:
                            blocks.append(value)
    if not blocks:
        raise ValueError("No readable body text found in this Word document")
    return GroundTruthDraft(
        source_path=str(original.resolve()),
        text="\n".join(blocks),
        blocks=tuple(blocks),
        warning=("This is a verbatim extraction preview, NOT a verified scoring "
                 "reference. Speaker labels, headings and notes remain until "
                 "the researcher reviews and edits them."),
    )
