import json
import tempfile
import unittest
from pathlib import Path
from journey_receipt import emit, expected_owner

SHA = 'a' * 40
MODE = 'sql-only-ci'


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)

    def fixture(self, stage, key=None, value=None, empty=None):
        for label in ('a', 'b'):
            doc = expected_owner(label)
            if label == 'a' and key:
                doc[key] = value
            no_context = empty if empty is not None and label == 'a' else [0, 0]
            (self.p / f'journey-{stage}-{label}.private').write_text(
                json.dumps(doc) + '\n' + json.dumps(no_context) + '\n')

    def baseline(self):
        self.fixture('before')
        return emit(self.p, 'before', MODE, SHA)

    def test_all_stages(self):
        self.baseline()
        for stage in ('after-refresh', 'after-send', 'after-restore'):
            self.fixture(stage)
            r = emit(self.p, stage, MODE, SHA)
            self.assertEqual(r['http_browser_action'], 'NOT_VERIFIED_BY_SQL')
            self.assertEqual(r['independent_restore_cluster'], stage == 'after-restore')

    def test_foreign_rejected(self):
        self.fixture('before', 'foreign', [1, 0])
        with self.assertRaises(ValueError): emit(self.p, 'before', MODE, SHA)
        self.assertFalse((self.p / 'journey-before.json').exists())

    def test_duplicate_rejected(self):
        self.fixture('before', 'page2', expected_owner('a')['page1'])
        with self.assertRaises(ValueError): emit(self.p, 'before', MODE, SHA)

    def test_send_write_rejected(self):
        self.fixture('before', 'counts', [3, 3, 0, 1, 0, 0])
        with self.assertRaises(ValueError): emit(self.p, 'before', MODE, SHA)

    def test_unscoped_leak_rejected(self):
        self.fixture('before', empty=[1, 0])
        with self.assertRaises(ValueError): emit(self.p, 'before', MODE, SHA)

    def test_changed_content_rejected(self):
        self.baseline()
        self.fixture('after-restore', 'detail', expected_owner('b')['detail'])
        with self.assertRaises(ValueError): emit(self.p, 'after-restore', MODE, SHA)

    def test_different_sha_rejected(self):
        self.baseline()
        self.fixture('after-restore')
        with self.assertRaises(ValueError): emit(self.p, 'after-restore', MODE, 'b'*40)

    def test_different_identity_mode_rejected(self):
        self.baseline()
        self.fixture('after-restore')
        with self.assertRaises(ValueError): emit(self.p, 'after-restore', 'verified-idp', SHA)

    def test_missing_baseline_rejected(self):
        self.fixture('after-restore')
        with self.assertRaises(OSError): emit(self.p, 'after-restore', MODE, SHA)

    def test_overwrite_rejected(self):
        self.baseline()
        with self.assertRaises(FileExistsError): emit(self.p, 'before', MODE, SHA)

    def test_bool_counts_rejected(self):
        self.fixture('before', 'foreign', [False, False])
        with self.assertRaises(ValueError): emit(self.p, 'before', MODE, SHA)

    def test_extra_field_rejected(self):
        self.fixture('before', 'secret', 'must never be exported')
        with self.assertRaises(ValueError): emit(self.p, 'before', MODE, SHA)


if __name__ == '__main__':
    unittest.main()
