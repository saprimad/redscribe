import subprocess
import sys
import tempfile
import unittest
from redscribe.benchmark.benchmark_output_lock import output_lock

class ProcessLockTests(unittest.TestCase):
    def test_process_termination_releases_lock(self):
        with tempfile.TemporaryDirectory() as d:
            code="import sys,time; from redscribe.benchmark.benchmark_output_lock import output_lock\nwith output_lock(sys.argv[1]):\n print('locked',flush=True)\n time.sleep(60)"
            p=subprocess.Popen([sys.executable,"-c",code,d],stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(p.stdout.readline().strip(),"locked")
                with self.assertRaises(RuntimeError):
                    with output_lock(d):
                        pass
            finally:
                p.kill()
                p.wait(timeout=10)
                p.stdout.close()
            with output_lock(d):
                pass
