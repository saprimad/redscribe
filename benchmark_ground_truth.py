"""Conservative DOCX extraction for researcher-reviewed ASR references.

No speaker labels, headings, fillers or dialect words are discarded automatically.
Paragraphs and table cells are kept in document XML order. User must review text
before approving it for scoring. The original DOCX is read-only.
"""
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256

from docx import Document
from docx.oxml.ns import qn


@dataclass(frozen=True)
class GroundTruthDraft:
    source_path: str
    text: str
    blocks: tuple[str, ...]
    warning: str
    source_sha256: str = ""
    issues: tuple[str, ...] = ()
    extraction_version: str = "body-order-v2"


def extract_docx(path: str) -> GroundTruthDraft:
    original = Path(path)
    if not original.is_file() or original.suffix.lower() != ".docx":
        raise ValueError("Choose an existing .docx document")
    if original.name.startswith("~$"):
        raise ValueError("Temporary Word lock files cannot be references")
    # Capture source bytes before preview; re-check at final approval.
    source_sha256 = sha256(original.read_bytes()).hexdigest()
    doc = Document(str(original))
    blocks = []
    issues = []
    body_xml = doc.element.body
    for tag, name in (
        ("w:ins", "tracked insertions"),
        ("w:del", "tracked deletions"),
        ("w:commentRangeStart", "comment anchors"),
        ("w:txbxContent", "text boxes"),
        ("w:fldChar", "Word fields"),
    ):
        if any(True for _ in body_xml.iter(qn(tag))):
            issues.append(f"Document contains {name}; extraction requires visual review")
    # Header/footer content is not included in the body-order preview.
    if any(p.text.strip() for section in doc.sections
           for p in list(section.header.paragraphs) + list(section.footer.paragraphs)):
        issues.append("Header/footer text is excluded from the scoring preview")

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
        warning=("Unverified extraction: verify audio coverage, speaker labels, "
                 "headings, notes, fillers and flagged Word features. "
                 "No text is automatically removed."),
        source_sha256=source_sha256,
        issues=tuple(issues),
    )
