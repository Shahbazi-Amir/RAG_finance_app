"""Transfer regression for live helper predicates (unit-only)."""
import unittest
from browser_privacy_paging import no_store, checked_denial, checked_message_page, validate_fixture, check_origin


class TestTransfer(unittest.TestCase):
    def test_cache_controls(self):
        for value in ("no-store","private, no-store","NO-STORE, max-age=0"):
            with self.subTest(value=value):self.assertTrue(no_store({"cache-control":value}))
        for value in ("","x-no-store",'private, foo="no-store"',"public, no-store",'no-store="x"','no-store, foo="'):
            with self.subTest(value=value):self.assertFalse(no_store({"cache-control":value}))

    def test_private_denials(self):
        headers={"cache-control":"no-store"}
        checked_denial(404,headers,'{"error":"NOT_FOUND"}',("privateA",),expected=404)
        for body in ('{"value":"privateA"}',r'{"value":"\u0070rivateA"}',r'{"\u0070rivateA":1}'):
            with self.subTest(body=body),self.assertRaises(AssertionError):
                checked_denial(404,headers,body,("privateA",),expected=404)
        with self.assertRaises(AssertionError):checked_denial(200,headers,"",(),expected=404)
        with self.assertRaises(AssertionError):checked_denial(404,{},"",(),expected=404)

    def test_page(self):
        body={"owner_user_id":"ownerA","items":[{"message_id":"m1","text":"question"}],"page":{"has_more":True,"next_cursor":"c1"}}
        self.assertEqual(checked_message_page(body,"ownerA",{"m1":"question"},set(),1),(["m1"],"c1"))
        for owner,expected,seen,limit in (("ownerB",{"m1":"question"},set(),1),("ownerA",{"m1":"other"},set(),1),("ownerA",{"m1":"question"},{"m1"},1),("ownerA",{"m1":"question"},set(),2)):
            with self.subTest(owner=owner,seen=seen,limit=limit),self.assertRaises(AssertionError):
                checked_message_page(body,owner,expected,seen,limit)
        for more,cursor in ((True,None),(True,"?"),(False,"c1"),(1,"c1")):
            body["page"]={"has_more":more,"next_cursor":cursor}
            with self.subTest(more=more,cursor=cursor),self.assertRaises(AssertionError):
                checked_message_page(body,"ownerA",{"m1":"question"},set(),1)

    def test_fixture(self):
        rows=[("ownerA","cidA","a"),("ownerB","cidB","b")]
        messages=[("ownerA","cidA","midA","F3_REAL_POSTGRES_A_0")]
        selected,markers,ids_a,ids_b,forbidden=validate_fixture(rows,"ownerA","ownerB",messages)
        self.assertEqual(selected,messages[0])
        self.assertIn("midA",forbidden)
        self.assertIn("ownerA",forbidden)
        self.assertEqual(ids_b,("cidB",))
        with self.assertRaises(AssertionError):validate_fixture(rows,"ownerA","ownerA",messages)
        with self.assertRaises(AssertionError):validate_fixture(rows,"ownerA","ownerB",messages*2)

    def test_origin(self):
        check_origin("https://127.0.0.1:3443")
        for origin in ("http://127.0.0.1:3443","https://example.invalid","https://127.0.0.1:3443/path"):
            with self.subTest(origin=origin),self.assertRaises(AssertionError):check_origin(origin)
