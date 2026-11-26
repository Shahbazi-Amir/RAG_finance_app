import base64,io,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts/phase3'))
from f3_lab_log_guard import scan

class Tests(unittest.TestCase):
    def check(self,raw): return scan(io.BytesIO(raw), [('test_literal',b'fictional+test/secret')])
    def test_encoded(self):
        for raw in (b'fictional%2Btest%2Fsecret',base64.b64encode(b'fictional+test/secret')):
            self.assertEqual(self.check(raw)['result'],'LEAK_FOUND')
    def test_jwt(self):
        self.assertIn('jwt_shape',self.check(b'eyJAAAAAAAAAAAA.BBBBBBBBBBBBBB.CCCCCCCCCCCCCCCCC')['matches'])
    def test_cookie(self):
        self.assertIn('session_cookie_shape',self.check(b'__Host-rag-session='+b'A'*24)['matches'])
    def test_auth(self):
        self.assertIn('authorization_shape',self.check(b'BFF-Assertion '+b'A'*24)['matches'])
    def test_oauth(self):
        self.assertIn('oauth_query_shape',self.check(b'/callback?code='+b'A'*24)['matches'])
    def test_safe_label(self):
        self.assertEqual(self.check(b'Authorization: REDACTED; code=200; login succeeded')['result'],'NO_LITERAL_MATCHES')
    def test_receipt_no_values(self):
        value=b'fictional+test/secret'
        self.assertNotIn(value.decode(),json.dumps(self.check(value)))

    def test_mixed_percent_encoding(self):
        self.assertEqual(self.check(b'fictional%2btest%2fsecret')['result'],'LEAK_FOUND')
    def test_partial_percent_encoding(self):
        self.assertEqual(self.check(b'%66ictional+test%2fsecret')['result'],'LEAK_FOUND')
    def test_unpadded_base64(self):
        self.assertEqual(self.check(base64.urlsafe_b64encode(b'fictional+test/secret').rstrip(b'='))['result'],'LEAK_FOUND')
    def test_encoded_oauth(self):
        self.assertIn('oauth_query_shape',self.check(b'/callback%3Fcode%3D'+b'A'*24)['matches'])
    def test_json_escaped_literal(self):
        value='synthetic-\u0645\u0627\u0644\u06cc'.encode('utf-8')
        escaped=json.dumps(value.decode(),ensure_ascii=True).encode()
        self.assertEqual(scan(io.BytesIO(escaped),[('synthetic_identity',value)])['result'],'LEAK_FOUND')
    def test_double_encoded_canonical_literal(self):
        self.assertEqual(self.check(b'fictional%252Btest%252Fsecret')['result'],'LEAK_FOUND')
    def test_nonrecursive_decode_boundary(self):
        self.assertEqual(self.check(b'fictional%25252btest%25252fsecret')['result'],'NO_LITERAL_MATCHES')

if __name__=='__main__': unittest.main()
