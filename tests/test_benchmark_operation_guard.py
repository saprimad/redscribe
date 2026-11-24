import threading
import unittest
from redscribe.ui.operation_guard import start_exclusive

class OperationGuardTests(unittest.TestCase):
    def test_exclusion_until_worker_returns(self):
        release=threading.Event()
        t=start_exclusive(lambda:release.wait(5))
        try:
            self.assertIsNotNone(t)
            self.assertIsNone(start_exclusive(lambda:None))
        finally:
            release.set()
            t.join(5)
        t2=start_exclusive(lambda:None)
        self.assertIsNotNone(t2)
        t2.join(5)
