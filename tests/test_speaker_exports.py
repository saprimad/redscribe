"""Verify speaker colours and unchanged research content in actual exports."""
import importlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from docx import Document
from openpyxl import load_workbook
from speaker_styles import speaker_colour, speaker_fill, UNKNOWN_COLOUR

# Exporters do not need an installed ASR engine or any model downloads.
original_engine = sys.modules.get("faster_whisper")
sys.modules["faster_whisper"] = SimpleNamespace(WhisperModel=Mock())
try:
    app = importlib.import_module("redscribe_gpu")
finally:
    if original_engine is None:
        sys.modules.pop("faster_whisper", None)
    else:
        sys.modules["faster_whisper"] = original_engine


def example_rows():
    return [dict(speaker=speaker, start_s=i * 10, end_s=i * 10 + 8,
                 text=f"Example utterance {i + 1}.")
            for i, speaker in enumerate(("SPEAKER_03", "SPEAKER_05", "UNKNOWN", "SPEAKER_01",
                                         "SPEAKER_02", "SPEAKER_00", "SPEAKER_04", "SPEAKER_03"))]


def export_examples(directory):
    rows = example_rows()
    kwargs = dict(utterance_rows=rows, segment_ranges=[(row['start_s'], row['end_s']) for row in rows],
                  audio_path="example.wav", audio_duration_s=80, processing_minutes=1.2,
                  detected_language="ms", meta_from_gui={"project": "Example study", "researcher": "Example researcher"},
                  actual_device="cpu", actual_compute_type="int8", whisper_model="large-v3",
                  diarization_enabled=True, diarization_status="Completed", diarization_model=app.DIARIZATION_MODEL)
    xlsx = Path(directory) / "speaker_colours.xlsx"
    docx = Path(directory) / "speaker_colours.docx"
    app.save_xlsx_with_early_report(xlsx_path=str(xlsx), **kwargs)
    app.save_docx_transcript(docx_path=str(docx), **kwargs)
    return xlsx, docx


class SpeakerColourTests(unittest.TestCase):
    def test_six_detected_speaker_ids_have_distinct_readable_accents(self):
        colours = [speaker_colour(f"SPEAKER_{i:02}") for i in range(6)]
        self.assertEqual(len(set(colours)), 6)
        for colour in colours:
            self.assertRegex(colour, r"^[0-9A-F]{6}$")
            self.assertNotEqual(colour, "FFFFFF")

    def test_mapping_is_stable_with_reordered_inputs_and_unknowns(self):
        ids = ("SPEAKER_03", "SPEAKER_05", "SPEAKER_00", "Custom interviewer")
        colours = {speaker: speaker_colour(speaker) for speaker in ids}
        self.assertEqual(colours, {speaker: speaker_colour(speaker) for speaker in reversed(ids)})
        self.assertEqual(speaker_colour("speaker_03"), colours["SPEAKER_03"])
        self.assertEqual(speaker_colour(None), UNKNOWN_COLOUR)
        self.assertEqual(speaker_colour("UNKNOWN"), UNKNOWN_COLOUR)
        self.assertNotEqual(speaker_fill("SPEAKER_03"), colours["SPEAKER_03"])


class SpeakerExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.xlsx, cls.docx = export_examples(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_excel_speaker_cells_match_shared_palette_and_preserve_values(self):
        book = load_workbook(self.xlsx)
        sheet = book['Transcription']
        self.assertEqual(sheet.max_column, 7)
        for i, row in enumerate(example_rows(), start=2):
            speaker = sheet.cell(i, 2)
            self.assertEqual(speaker.value, row['speaker'])
            self.assertEqual(speaker.font.color.rgb[-6:], speaker_colour(row['speaker']))
            self.assertTrue(speaker.font.bold)
            self.assertEqual(speaker.fill.fgColor.rgb[-6:], speaker_fill(row['speaker']))
            self.assertEqual(sheet.cell(i, 5).value, row['text'])
            self.assertIsNone(sheet.cell(i, 6).value)
            self.assertIsNone(sheet.cell(i, 7).value)
            self.assertEqual(sheet.cell(i, 3).value, app.sec_to_hms(row['start_s']))
        summary = book['Early_Report']
        speaker_cells = [row[0] for row in summary if str(row[0].value).startswith('SPEAKER_')]
        self.assertEqual(len(speaker_cells), 6)
        for cell in speaker_cells:
            self.assertEqual(cell.font.color.rgb[-6:], speaker_colour(cell.value))
        self.assertEqual(len(summary._charts), 2)
        book.close()

    def test_word_speaker_runs_match_palette_without_recolouring_transcript_text(self):
        document = Document(self.docx)
        paragraphs = [p for p in document.paragraphs if any(r.text.endswith(': ') for r in p.runs)]
        turns = app.group_consecutive_speaker_turns(example_rows())
        self.assertEqual(len(paragraphs), len(turns))
        for paragraph, row in zip(paragraphs, turns):
            label = next(run for run in paragraph.runs if run.text == f"{row['speaker']}: ")
            self.assertEqual(str(label.font.color.rgb), speaker_colour(row['speaker']))
            self.assertTrue(label.bold)
            self.assertEqual(paragraph.runs[-1].text, row['text'])
            self.assertIsNone(paragraph.runs[-1].font.color.rgb)
            self.assertTrue(paragraph.text.startswith(f"[{app.sec_to_hms(row['start_s'])}"))
        summary = next(t for t in document.tables if t.rows[0].cells[0].text == 'Speaker')
        for row in summary.rows[1:]:
            self.assertEqual(str(row.cells[0].paragraphs[0].runs[0].font.color.rgb), speaker_colour(row.cells[0].text))
