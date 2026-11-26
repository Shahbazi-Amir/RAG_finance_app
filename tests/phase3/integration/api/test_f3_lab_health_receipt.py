import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/"scripts/phase3"))
from f3_lab_health_receipt import build,STAGES,EXPECTED
class Tests(unittest.TestCase):
    def events(self):
        return [dict(stage=s,http_status=h,monotonic_ns=(i+1)*1000000) for i,(s,h) in enumerate(zip(STAGES,EXPECTED))]
    def test_transitions(self):
        d=build(self.events(),"a"*40)
        self.assertEqual([x["alert_transition"] for x in d["health"]],["NONE","OPEN","RESOLVE","NONE"])
        self.assertEqual(d["acceptance"],"NOT_ACCEPTED")
    def test_missing(self):
        with self.assertRaises(ValueError):build(self.events()[:-1],"a"*40)
    def test_false_recovery(self):
        e=self.events();e[2]["http_status"]=503
        with self.assertRaises(ValueError):build(e,"a"*40)
    def test_wrong_stage(self):
        e=self.events();e[1]["stage"]="restore"
        with self.assertRaises(ValueError):build(e,"a"*40)
    def test_reverse_clock(self):
        e=self.events();e[1]["monotonic_ns"]=0
        with self.assertRaises(ValueError):build(e,"a"*40)
    def test_extra_field(self):
        e=self.events();e[1]["unapproved"]="fixture"
        with self.assertRaises(ValueError):build(e,"a"*40)
    def test_bad_sha(self):
        with self.assertRaises(ValueError):build(self.events(),"main")
if __name__=="__main__":unittest.main()
