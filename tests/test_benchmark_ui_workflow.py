import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from redscribe.ui.benchmark_ui import BenchmarkWindow
from redscribe.ui.benchmark_reference_ui import GroundTruthReview


class BenchmarkUIWorkflowTests(unittest.TestCase):
    def test_review_opens_before_master_folder_selection(self):
        window = BenchmarkWindow.__new__(BenchmarkWindow)
        window.window = Mock()
        window.reference_files = ("example.docx",)
        window.master_folder = Mock()
        with patch("redscribe.ui.benchmark_reference_ui.open_ground_truth_review") as review:
            window.open_reference_review()
            review.assert_called_once()
            window.master_folder.assert_not_called()
            self.assertTrue(callable(review.call_args.kwargs["output_provider"]))

    def test_approval_registers_canonical_path(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "reference.docx"
            source.touch()
            window = BenchmarkWindow.__new__(BenchmarkWindow)
            window.reference_files = (str(source.resolve()),)
            window.approved_references = {}
            window.batch_pairs = ()
            window.reference_summary = Mock()
            window.mark_reference_approved(str(source), "reference.json")
            self.assertEqual(window.approved_references[str(source.resolve())], "reference.json")

    def test_cancel_storage_does_not_freeze_or_clear_approval(self):
        review = GroundTruthReview.__new__(GroundTruthReview)
        review.window = Mock()
        review.current_draft = Mock()
        review.acknowledged = Mock()
        review.acknowledged.get.return_value = True
        review.verification = {k: Mock() for k in ("audio_verified", "coverage_verified",
            "speaker_labels_reviewed", "non_speech_reviewed")}
        for flag in review.verification.values():
            flag.get.return_value = True
        review.text = Mock()
        review.text.get.return_value = "hmm kawe"
        review.output_dir = None
        review.output_provider = Mock(return_value=None)
        with patch("redscribe.ui.benchmark_reference_ui.messagebox.askyesno", return_value=True), patch(
            "redscribe.ui.benchmark_reference_ui.approve_reference"
        ) as freeze:
            review.approve()
            review.output_provider.assert_called_once()
            freeze.assert_not_called()
            review.acknowledged.set.assert_not_called()
