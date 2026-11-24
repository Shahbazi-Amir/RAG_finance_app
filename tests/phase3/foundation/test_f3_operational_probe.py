"""Offline invariants for the lab observer; runtime measurements separate."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("probe",ROOT/"tests/phase3/integration/foundation/f3_operational_probe.py")
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

class LabObserverTest(unittest.TestCase):
    def test_percentiles_status_and_throughput(self):
        doc=probe.summary([(200,10),(200,20),(503,30),(200,40)],2)
        self.assertEqual(doc["requests"],4)
        self.assertEqual(doc["http_5xx"],1)
        self.assertEqual(doc["requests_per_second"],2)
        self.assertEqual(doc["p50_ms"],20)
        self.assertEqual(doc["p95_ms"],40)
        self.assertEqual(doc["p99_ms"],40)

    def test_phase4_negative_rejects_activated_table(self):
        conn=Mock();conn.__enter__=Mock(return_value=conn);conn.__exit__=Mock(return_value=False)
        conn.execute.return_value=[("messages",),("conversations",)]
        self.assertEqual(probe.phase4_negative(lambda:conn)["active_reserved_tables"],0)
        conn.execute.return_value=[("financial_profiles",)]
        with self.assertRaises(AssertionError):probe.phase4_negative(lambda:conn)

    def test_dashboard_escapes_untrusted_input(self):
        receipt={"sha":"<script>forbidden</script>","operational_probe":{"stages":[{
          "concurrency":1,"measurement":probe.summary([(200,1)],1),
          "resource_sample":{"api":{"cpu_pct":0},"web":{"cpu_pct":0},"postgres":{"database_connections":1}}
        }]}}
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"health.html";probe.write_dashboard(receipt,target)
            text=target.read_text()
            self.assertNotIn("<script>",text)
            self.assertIn("&lt;script&gt;",text)
            self.assertIn("Not target acceptance",text)
if __name__=="__main__":unittest.main()
