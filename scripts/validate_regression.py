"""Run unittest discovery from the repository root. Fail on any skip or empty suite."""
import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test*.py")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover("tests", pattern=args.pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"Executed {result.testsRun} tests, failures={len(result.failures)}, "
          f"errors={len(result.errors)}, skipped={len(result.skipped)}")
    return 0 if result.testsRun and result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    sys.exit(main())
