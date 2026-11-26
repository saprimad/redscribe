import tempfile
from pathlib import Path
from matplotlib.backends.backend_pdf import PdfPages
import unittest
from unittest.mock import patch
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from redscribe.benchmark.benchmark_publication import export_publication


class FigureValuesTests(unittest.TestCase):
    def test_common_cohort_units_and_missing_values(self):
        def row(n, errors, audio, inference):
            return dict(status="completed", wer=errors/n, cer=errors/n,
                        word_substitutions=errors, word_deletions=0,
                        word_insertions=0, reference_words=n,
                        char_substitutions=errors, char_deletions=0,
                        char_insertions=0, reference_characters=n,
                        audio_seconds=audio, inference_seconds=inference)
        state = {"identity": {"models": ["a", "b"], "recordings": ["P1", "P2", "P3"]},
                 "results": {"a": {"P1": row(10, 1, 10, 2),
                                   "P2": row(90, 45, 30, 12),
                                   "P3": row(10, 9, 10, 2)},
                             "b": {"P1": row(10, 2, 10, 1),
                                   "P2": row(90, 18, 30, 3),
                                   "P3": {"status": "failed"}}}}
        figures = {}
        medians = {}
        original_boxplot = Axes.boxplot
        def capture_boxplot(ax, *args, **kwargs):
            artists = original_boxplot(ax, *args, **kwargs)
            medians[ax] = artists['medians']
            return artists
        original_savefig = Figure.savefig
        def capture(fig, path, **kwargs):
            if isinstance(path, PdfPages):
                return original_savefig(fig, path, **kwargs)
            figures[Path(path).stem] = fig.axes[0]
        with tempfile.TemporaryDirectory() as d, patch.object(Figure, "savefig", capture), patch.object(Axes, "boxplot", capture_boxplot):
            export_publication(d, state)
            pdf = Path(d) / 'scientific_report.pdf'
            self.assertTrue(pdf.read_bytes().startswith(b'%PDF-'))
        accuracy = figures["corpus_accuracy"]
        self.assertEqual(accuracy.get_ylabel(), "Error rate (%)")
        for actual, expected in zip([p.get_height() for p in accuracy.patches], [46, 20, 46, 20]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(len(accuracy.patches), 4)
        for metric in ("wer", "cer"):
            ax = figures[metric + "_distribution"]
            self.assertEqual(ax.get_ylabel(), "Recording " + metric.upper() + " (%)")
            self.assertEqual([t.get_text() for t in ax.get_xticklabels()], ["a", "b"])
            self.assertEqual(len(medians[ax]), 2)
            self.assertAlmostEqual(medians[ax][0].get_ydata()[0], 30)
            self.assertAlmostEqual(medians[ax][1].get_ydata()[0], 20)
        speed = figures["accuracy_speed"]
        self.assertEqual(speed.get_xlabel(), "Aggregate real-time factor")
        for collection, expected in zip(speed.collections, [(0.35, 46), (0.1, 20)]):
            for actual, value in zip(collection.get_offsets()[0], expected):
                self.assertAlmostEqual(actual, value)
        self.assertEqual(len(speed.collections), 2)
        heat = figures["participant_wer_heatmap"].images[0].get_array()
        self.assertEqual(heat.shape, (3, 2))
        self.assertAlmostEqual(heat[2, 0], 90)
        self.assertTrue(heat.mask[2, 1])
