"""Overlap helper regression tests. Synthetic page doubles, not browser acceptance."""
import contextlib, io, unittest
from f3_lab_read_load import _START, _COLLECT, _windows, _overlap_count, measure_cross_context_overlap

class Page:
    url='https://ragfinance.ir/'
    def __init__(self, role, offset=0, fail=False, fail_start=False):
        self.role=role; self.offset=offset; self.fail=fail; self.fail_start=fail_start; self.calls=[]
    def evaluate(self, script, args=None):
        if script==_START:
            self.calls.append('start')
            if self.fail_start: raise RuntimeError('start')
            return True
        assert script==_COLLECT
        self.calls.append('collect')
        if self.fail: return {'ok':False}
        t=1000000+self.offset
        return {'ok':True,'value':{'samples':[1000]*4,'statuses':{'200':4} if self.role=='a' else {'200':2,'404':2},'cursor':'private-cursor' if self.role=='a' else None,'windows':[[t,t+100]]*4}}

class TestOverlap(unittest.TestCase):
    def run_probe(self,a,b):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            r=measure_cross_context_overlap(a,b,'private-a','private-b','source')
        return r,out.getvalue()
    def test_overlap_redacted(self):
        a,b=Page('a'),Page('b',50)
        r,log=self.run_probe(a,b)
        self.assertEqual(r['overlapping_request_pairs'],16)
        self.assertEqual(r['requests'],8)
        self.assertNotIn('private-',log)
        self.assertNotIn('1000000',log)
        self.assertEqual(a.calls,b.calls)
    def test_no_overlap_fails_after_two(self):
        a,b=Page('a'),Page('b',100)
        with self.assertRaisesRegex(AssertionError,'no cross-context'):self.run_probe(a,b)
        self.assertEqual(a.calls,['start','collect']*2)
    def test_failure_drains_both(self):
        a,b=Page('a',fail=True),Page('b')
        with self.assertRaises(AssertionError):self.run_probe(a,b)
        self.assertEqual(b.calls,['start','collect'])
    def test_second_start_failure_drains_first(self):
        a,b=Page('a'),Page('b',fail_start=True)
        with self.assertRaises(RuntimeError):self.run_probe(a,b)
        self.assertEqual(a.calls,['start','collect'])
    def test_bad_window_rejected(self):
        for pair in ([True,2],[2,1],[1,7000002],[0,1],[1,2**53]):
            with self.subTest(pair=pair),self.assertRaises(AssertionError):
                _windows({'samples':[1],'statuses':{'200':1},'cursor':None,'windows':[pair]},1)
    def test_zero_and_touching_not_overlap(self):
        self.assertEqual(_overlap_count([[1,2],[3,3]],[[2,4]]),0)
    def test_wrong_origin_or_same_context(self):
        a,b=Page('a'),Page('b');b.url='https://example.invalid/'
        with self.assertRaises(ValueError):self.run_probe(a,b)
        with self.assertRaises(ValueError):self.run_probe(a,a)
if __name__=='__main__':unittest.main()
