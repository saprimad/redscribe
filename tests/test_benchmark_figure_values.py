import tempfile
import unittest
from unittest.mock import patch
from matplotlib.figure import Figure
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
        def capture(fig, path, **kwargs):
            figures[path.stem] = fig.axes[0]
        with tempfile.TemporaryDirectory() as d, patch.object(Figure, "savefig", capture):
            export_publication(d, state)
        accuracy = figures["corpus_accuracy"]
        self.assertEqual(accuracy.get_ylabel(), "Error rate (%)")
        for actual, expected in zip([p.get_height() for p in accuracy.patches], [46, 20, 46, 20]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(len(accuracy.patches), 4)
        for metric in ("wer", "cer"):
            ax = figures[metric + "_distribution"]
            self.assertEqual(ax.get_ylabel(), "Recording " + metric.upper() + " (%)")
            self.assertEqual([t.get_text() for t in ax.get_xticklabels()], ["a", "b"])
            # Matplotlib boxplot line order: whiskers, caps, median, fliers.
            self.assertAlmostEqual(ax.lines[4].get_ydata()[0], 30)
            self.assertAlmostEqual(ax.lines[10].get_ydata()[0], 20)
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
