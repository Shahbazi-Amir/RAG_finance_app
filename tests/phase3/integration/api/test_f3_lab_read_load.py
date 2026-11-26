import contextlib,io,json,unittest
from f3_lab_read_load import _receipt,measure_bounded_load,_measure

class Page:
    url='https://ragfinance.ir/'
    def __init__(self,role): self.role=role; self.calls=[]
    def evaluate(self,js,args):
        self.calls.append(args)
        n=args['width']*args['rounds']
        lists=sum((i+j)%2==0 for i in range(args['rounds']) for j in range(args['width']))
        status={'200':n} if self.role=='a' else {'200':lists,'404':n-lists}
        if args['extraChecks']:
            status['200']+=3;status['404']=status.get('404',0)+1
        if args['checkCursor'] is not None: status['422']=3
        return {'samples':[1000000]*n,'statuses':status,'cursor':'private-cursor' if self.role=='a' else None}

class Tests(unittest.TestCase):
    def test_counts_and_redaction(self):
        a,b=Page('a'),Page('b')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            r=measure_bounded_load(a,b,'private-owner-a','private-owner-b','source')
        self.assertEqual(r['requests'],53)
        self.assertEqual(len(r['tiers']),3)
        self.assertEqual([x['width'] for x in a.calls],[1,2,4])
        self.assertIsNone(b.calls[0]['checkCursor'])
        self.assertEqual(b.calls[-1]['checkCursor'],'private-cursor')
        for value in ('private-owner','private-cursor'):
            self.assertNotIn(value,out.getvalue())
    def test_wrong_scope(self):
        a,b=Page('a'),Page('b')
        for x,y,stage in [('same','same','source'),('a','b','production'),('','b','restore')]:
            with self.assertRaises(ValueError): measure_bounded_load(a,b,x,y,stage)
        a.url='https://example.invalid/'
        with self.assertRaises(ValueError): measure_bounded_load(a,b,'a','b','source')
    def test_missing_samples(self):
        with self.assertRaises(AssertionError): _receipt({'samples':[],'statuses':{'200':1},'cursor':None},1,'a')
    def test_unexpected_status(self):
        with self.assertRaises(AssertionError): _receipt({'samples':[1],'statuses':{'503':1},'cursor':None},1,'a')
    def test_wrong_total(self):
        with self.assertRaises(AssertionError): _receipt({'samples':[1],'statuses':{'200':2},'cursor':None},1,'a')
    def test_extra_data_not_returned(self):
        with self.assertRaises(AssertionError): _receipt({'samples':[1],'statuses':{'200':1},'cursor':None,'body':'secret'},1,'a')
    def test_boolean_status(self):
        with self.assertRaises(AssertionError): _receipt({'samples':[1],'statuses':{'200':True},'cursor':None},1,'a')
    def test_b_needs_both_results(self):
        with self.assertRaises(AssertionError): _receipt({'samples':[1,2],'statuses':{'200':2},'cursor':None},2,'b')

    def test_exact_success_count(self):
        with self.assertRaises(AssertionError):
            _receipt({'samples':[1,2],'statuses':{'200':2,'404':1},'cursor':None},2,'b',1,expected_200=1,expected_404=1)
    def test_foreign_must_be_404(self):
        with self.assertRaises(AssertionError):
            _receipt({'samples':[1,2],'statuses':{'200':1,'422':2},'cursor':None},2,'b',1,expected_200=1,expected_404=1)
    def test_foreign_count_with_404_negative(self):
        r=_receipt({'samples':[1,2],'statuses':{'200':1,'404':2},'cursor':None},2,'b',1,expected_200=1,expected_404=1)
        self.assertEqual(r['http_status_counts']['404'],2)

if __name__=='__main__': unittest.main()
