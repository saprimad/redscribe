"""Dependency-free, auditable XLSX presentation for experimental ASR results.

Uses only Python's standard-library ZIP/XML support, so the benchmark does not
need another runtime dependency. Values are derived from benchmark_reporting;
no linguistic normalisation, re-scoring, or invented outcome values occur.
"""
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
import json
import math
import os
import sys
import tempfile
import zipfile

from benchmark_reporting import build_summary, build_error_breakdown

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

SHEETS = (
    ("Model Summary", (
        ("cohort", "Cohort"), ("model_key", "ASR Model"),
        ("recordings_total", "Audio total"), ("recordings_completed", "Completed"),
        ("recordings_failed", "Failed"), ("recordings_cancelled", "Cancelled"),
        ("recordings_not_run", "Not run"), ("recordings_unavailable", "Unavailable"),
        ("word_scored", "WER N"), ("character_scored", "CER N"),
        ("corpus_wer", "Corpus WER (%)"), ("corpus_cer", "Corpus CER (%)"),
        ("macro_wer", "Macro WER (%)"), ("macro_cer", "Macro CER (%)"),
    )),
    ("Recording Results", (
        ("audio", "Audio"), ("model_key", "ASR Model"), ("status", "Status"),
        ("wer", "Raw WER (%)"), ("cer", "Raw CER (%)"), ("error", "Error / reason"),
        ("audio_sha256", "Audio SHA-256"),
    )),
    ("Error Breakdown", (
        ("audio", "Audio"), ("model_key", "ASR Model"), ("status", "Status"),
        ("word_substitutions", "Word S"), ("word_deletions", "Word D"),
        ("word_insertions", "Word I"), ("reference_words", "Reference words"),
        ("char_substitutions", "Char S"), ("char_deletions", "Char D"),
        ("char_insertions", "Char I"), ("reference_characters", "Reference characters"),
        ("wer", "WER (%)"), ("cer", "CER (%)"),
    )),
    ("Run Status", (
        ("audio", "Audio"), ("status", "Recording status"),
        ("error", "Recording error"), ("audio_sha256", "Audio SHA-256"),
    )),
)


def _safe_xml(value):
    """XML 1.0 permits printable Unicode, tab, LF and CR only."""
    return "".join(ch for ch in str(value)
                   if ch in "\t\n\r" or ord(ch) >= 32 and
                   not 0xD800 <= ord(ch) <= 0xDFFF and
                   ord(ch) not in (0xFFFE, 0xFFFF))


def _col(index):
    name = ""
    while index:
        index, digit = divmod(index - 1, 26)
        name = chr(65 + digit) + name
    return name


def _xml(root):
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(
        root, encoding="utf-8")


def _cell(row_element, column, row_number, value, percentage=False, heading=False):
    if value is None or value == "":
        return
    attrs = {"r": f"{_col(column)}{row_number}", "s": "1" if heading else
             ("2" if percentage and isinstance(value, (int, float)) else "0")}
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        cell = SubElement(row_element, f"{{{MAIN}}}c", attrs)
        SubElement(cell, f"{{{MAIN}}}v").text = str(value)
    else:
        # Inline strings prevent '=HYPERLINK(...)' and similar formula injection.
        cell = SubElement(row_element, f"{{{MAIN}}}c", {**attrs, "t": "inlineStr"})
        inline = SubElement(cell, f"{{{MAIN}}}is")
        SubElement(inline, f"{{{MAIN}}}t", {XML_SPACE: "preserve"}).text = _safe_xml(value)


def _sheet_xml(headers, rows, percent_columns):
    root = Element(f"{{{MAIN}}}worksheet")
    SubElement(root, f"{{{MAIN}}}dimension",
               {"ref": f"A1:{_col(len(headers))}{max(1, len(rows) + 1)}"})
    views = SubElement(root, f"{{{MAIN}}}sheetViews")
    view = SubElement(views, f"{{{MAIN}}}sheetView", {"workbookViewId": "0"})
    SubElement(view, f"{{{MAIN}}}pane",
               {"ySplit": "1", "topLeftCell": "A2", "activePane": "bottomLeft", "state": "frozen"})
    columns = SubElement(root, f"{{{MAIN}}}cols")
    for index, header in enumerate(headers, 1):
        width = 42 if header in ("Error / reason", "Recording error") else (
            65 if "SHA-256" in header else 28 if header in ("ASR Model", "Audio") else 19)
        SubElement(columns, f"{{{MAIN}}}col",
                   {"min": str(index), "max": str(index), "width": str(width), "customWidth": "1"})
    data = SubElement(root, f"{{{MAIN}}}sheetData")
    heading = SubElement(data, f"{{{MAIN}}}row", {"r": "1", "ht": "28", "customHeight": "1"})
    for index, title in enumerate(headers, 1):
        _cell(heading, index, 1, title, heading=True)
    for row_number, row_values in enumerate(rows, 2):
        row = SubElement(data, f"{{{MAIN}}}row", {"r": str(row_number)})
        for index, value in enumerate(row_values, 1):
            _cell(row, index, row_number, value, percentage=index - 1 in percent_columns)
    SubElement(root, f"{{{MAIN}}}autoFilter",
               {"ref": f"A1:{_col(len(headers))}{max(1, len(rows) + 1)}"})
    return _xml(root)


def _styles_xml():
    root = Element(f"{{{MAIN}}}styleSheet")
    fonts = SubElement(root, f"{{{MAIN}}}fonts", {"count": "2"})
    f = SubElement(fonts, f"{{{MAIN}}}font")
    SubElement(f, f"{{{MAIN}}}sz", {"val": "10"})
    SubElement(f, f"{{{MAIN}}}name", {"val": "Aptos"})
    heading = SubElement(fonts, f"{{{MAIN}}}font")
    SubElement(heading, f"{{{MAIN}}}b")
    SubElement(heading, f"{{{MAIN}}}sz", {"val": "10"})
    SubElement(heading, f"{{{MAIN}}}color", {"rgb": "FFFFFFFF"})
    SubElement(heading, f"{{{MAIN}}}name", {"val": "Aptos"})
    fills = SubElement(root, f"{{{MAIN}}}fills", {"count": "3"})
    SubElement(SubElement(fills, f"{{{MAIN}}}fill"), f"{{{MAIN}}}patternFill", {"patternType": "none"})
    SubElement(SubElement(fills, f"{{{MAIN}}}fill"), f"{{{MAIN}}}patternFill", {"patternType": "gray125"})
    pf = SubElement(SubElement(fills, f"{{{MAIN}}}fill"), f"{{{MAIN}}}patternFill",
                    {"patternType": "solid"})
    SubElement(pf, f"{{{MAIN}}}fgColor", {"rgb": "FF17324D"})
    SubElement(pf, f"{{{MAIN}}}bgColor", {"indexed": "64"})
    borders = SubElement(root, f"{{{MAIN}}}borders", {"count": "1"})
    SubElement(borders, f"{{{MAIN}}}border")
    csx = SubElement(root, f"{{{MAIN}}}cellStyleXfs", {"count": "1"})
    SubElement(csx, f"{{{MAIN}}}xf", {"numFmtId": "0", "fontId": "0",
                                    "fillId": "0", "borderId": "0"})
    xs = SubElement(root, f"{{{MAIN}}}cellXfs", {"count": "3"})
    SubElement(xs, f"{{{MAIN}}}xf", {"numFmtId": "0", "fontId": "0", "fillId": "0",
                                   "borderId": "0", "xfId": "0"})
    SubElement(xs, f"{{{MAIN}}}xf", {"numFmtId": "0", "fontId": "1", "fillId": "2",
                                   "borderId": "0", "xfId": "0", "applyFill": "1",
                                   "applyFont": "1"})
    SubElement(xs, f"{{{MAIN}}}xf", {"numFmtId": "10", "fontId": "0", "fillId": "0",
                                   "borderId": "0", "xfId": "0", "applyNumberFormat": "1"})
    styles = SubElement(root, f"{{{MAIN}}}cellStyles", {"count": "1"})
    SubElement(styles, f"{{{MAIN}}}cellStyle", {"name": "Normal", "xfId": "0", "builtinId": "0"})
    return _xml(root)


def _workbook_xml():
    root = Element(f"{{{MAIN}}}workbook",
                   {"xmlns:r": REL})
    sheets = SubElement(root, f"{{{MAIN}}}sheets")
    for index, (name, _) in enumerate(SHEETS, 1):
        SubElement(sheets, f"{{{MAIN}}}sheet",
                   {"name": name, "sheetId": str(index), f"{{{REL}}}id": f"rId{index}"})
    return _xml(root)


def _rels_xml():
    root = Element(f"{{{PKG}}}Relationships")
    for index in range(1, len(SHEETS) + 1):
        SubElement(root, f"{{{PKG}}}Relationship",
                   {"Id": f"rId{index}", "Type": f"{REL}/worksheet",
                    "Target": f"worksheets/sheet{index}.xml"})
    SubElement(root, f"{{{PKG}}}Relationship",
               {"Id": f"rId{len(SHEETS) + 1}", "Type": f"{REL}/styles",
                "Target": "styles.xml"})
    return _xml(root)


def _package_rels():
    root = Element(f"{{{PKG}}}Relationships")
    SubElement(root, f"{{{PKG}}}Relationship",
               {"Id": "rId1", "Type": f"{REL}/officeDocument", "Target": "xl/workbook.xml"})
    return _xml(root)


def _content_types():
    root = Element(f"{{{CONTENT}}}Types")
    SubElement(root, f"{{{CONTENT}}}Default",
               {"Extension": "rels", "ContentType":
                "application/vnd.openxmlformats-package.relationships+xml"})
    SubElement(root, f"{{{CONTENT}}}Default",
               {"Extension": "xml", "ContentType": "application/xml"})
    SubElement(root, f"{{{CONTENT}}}Override",
               {"PartName": "/xl/workbook.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"})
    SubElement(root, f"{{{CONTENT}}}Override",
               {"PartName": "/xl/styles.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"})
    for index in range(1, len(SHEETS) + 1):
        SubElement(root, f"{{{CONTENT}}}Override",
                   {"PartName": f"/xl/worksheets/sheet{index}.xml",
                    "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"})
    return _xml(root)


def export_excel(directory, state):
    """Create a workbook atomically from the same audited rows as reporting CSV."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    summary = build_summary(state)
    breakdown = build_error_breakdown(state)
    status = [{
        "audio": item["audio"], "status": item.get("status", "unknown"),
        "error": item.get("error", ""), "audio_sha256": item["audio_sha256"],
    } for item in state["items"]]
    table_rows = (summary, breakdown, breakdown, status)
    destination = folder / "benchmark_summary.xlsx"
    fd, tmpname = tempfile.mkstemp(prefix=".benchmark_summary_", suffix=".xlsx",
                                    dir=folder)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmpname, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", _content_types())
            archive.writestr("_rels/.rels", _package_rels())
            archive.writestr("xl/workbook.xml", _workbook_xml())
            archive.writestr("xl/_rels/workbook.xml.rels", _rels_xml())
            archive.writestr("xl/styles.xml", _styles_xml())
            for index, ((_, columns), records) in enumerate(zip(SHEETS, table_rows), 1):
                headers = [title for _, title in columns]
                values = [[row.get(key) for key, _ in columns] for row in records]
                percent = {col for col, (key, _) in enumerate(columns)
                           if key in ("wer", "cer", "corpus_wer", "corpus_cer",
                                      "macro_wer", "macro_cer")}
                archive.writestr(f"xl/worksheets/sheet{index}.xml",
                                 _sheet_xml(headers, values, percent))
        os.replace(tmpname, destination)
    finally:
        if os.path.exists(tmpname):
            os.unlink(tmpname)
    return destination


def export_from_manifest(manifest_path):
    """Export from an existing completed or incomplete single/batch JSON manifest."""
    manifest_path = Path(manifest_path)
    with manifest_path.open(encoding="utf-8") as stream:
        info = json.load(stream)
    if info.get("mode") == "batch":
        state = info
    elif info.get("pilot") is True:
        state = {
            "models": info["selected_models"],
            "items": [{
                "audio": info["source_audio"],
                "audio_sha256": info["audio_sha256"],
                "status": info["status"],
                "error": info.get("error", ""),
                "model_results": info.get("model_results", {}),
            }],
        }
    else:
        raise ValueError("Expected RedScribe single/batch benchmark manifest")
    return export_excel(manifest_path.parent, state)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python benchmark_excel.py PATH_TO_MANIFEST_JSON")
    print(export_from_manifest(sys.argv[1]))
