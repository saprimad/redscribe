import unittest
from types import SimpleNamespace
from benchmark_pilot import _assemble_segments

class NativeSegmentsTests(unittest.TestCase):
    def test_original_text_preserved(self):
        source = [" Hmm ", "", "kawe  dok", "\nsetuju "]
        sink = []
        result = _assemble_segments([SimpleNamespace(text=t, start=i, end=i+1)
                                     for i,t in enumerate(source)], sink)
        self.assertEqual([s["text"] for s in sink], source)
        self.assertEqual(result, "Hmm kawe  dok setuju")
        self.assertEqual(sink[0]["start"], 0)
