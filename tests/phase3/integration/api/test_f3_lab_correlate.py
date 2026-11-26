import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/"scripts/phase3"))
from f3_lab_correlate import match
class Tests(unittest.TestCase):
    def fixture(self):
        events=[dict(event="signed_history_read",route="list",status=200,elapsed_ms=2,request_id=f"{i:032x}",trace_id=f"{i+100:032x}") for i in range(48)]
        hashes=[hashlib.sha256(f"{e['request_id']}|{e['trace_id']}|{e['status']}".encode()).hexdigest() for e in events]
        return "F3_LAB_CORRELATION_HASHES "+json.dumps(dict(stage="source",hashes=hashes)),events
    def api(self,events):return "\n".join("api-1 | F3_HISTORY_EVENT "+json.dumps(e) for e in events)
    def test_match(self):
        b,e=self.fixture();self.assertEqual(match(b,self.api(e),"source"),48)
    def test_concatenated_api_events_denied(self):
        b,e=self.fixture()
        joined=self.api(e).replace("\n","",1)
        with self.assertRaises(ValueError):match(b,joined,"source")
    def test_truncated_browser_event_denied(self):
        b,e=self.fixture()
        with self.assertRaises(ValueError):match(b[:-1],self.api(e),"source")
    def test_missing(self):
        b,e=self.fixture()
        with self.assertRaises(ValueError):match(b,self.api(e[:-1]),"source")
    def test_duplicate(self):
        b,e=self.fixture()
        with self.assertRaises(ValueError):match(b,self.api(e+[e[0]]),"source")
    def test_wrong_stage(self):
        b,e=self.fixture()
        with self.assertRaises(ValueError):match(b,self.api(e),"restore")
    def test_extra_field(self):
        b,e=self.fixture();e[0]["secret"]="fixture"
        with self.assertRaises(ValueError):match(b,self.api(e),"source")
    def test_status_changed(self):
        b,e=self.fixture();e[0]["status"]=404
        with self.assertRaises(ValueError):match(b,self.api(e),"source")
if __name__=="__main__":unittest.main()
