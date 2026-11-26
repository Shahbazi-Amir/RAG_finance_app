"""Execute the changed log-guard shell function with offline command doubles.
No real Docker/PG, no production logs, no assertion of target redaction.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[4]
SCRIPT = REPO / 'infra/postgres/dev_f3_isolated/scripts/27_browser_app_only_pg_journey.sh'
FUNCTION = re.search(r'^scan_lab_logs\(\)\{\n.*?^\}', SCRIPT.read_text(), re.M | re.S).group(0)
ROLES = ('history_app','auth_revoker','auth_trust_api','auth_login_bootstrap','auth_login_claim_reader',
         'auth_login_issuer','auth_mapper','auth_login_binder','auth_login_reader')
SECRET = 'fictional-lab-secret-for-test-123'

class Tests(unittest.TestCase):
    def run_pipeline(self, stage='source', pg_log='postgres ready', app_log='app ready', pg_rc=0, app_rc=0):
        with tempfile.TemporaryDirectory() as tmp:
            runner=Path(tmp)
            work=runner/'isolated-work';root=work/'browser-journey'
            for directory in ('web','bootstrap','browser'):
                (root/directory).mkdir(parents=True)
            for path in ('web/proof','web/csrf','web/alias','bootstrap/seal'):
                (root/path).write_text(SECRET)
            for role in ROLES:
                (work/(role+'.password')).write_text(SECRET)
            (root/'browser/users.json').write_text(json.dumps({k:{f:SECRET+k+f for f in ('username','password','subject')} for k in ('a','b')}))
            env={**os.environ,'CI':'true','GITHUB_ACTIONS':'true','RUNNER_TEMP':str(runner),'SOURCE_REPO':str(REPO),
                 'F3_BROWSER_ROOT':str(root),'LAB_WORK':str(work),'TEST_PG_LOG':pg_log,'TEST_APP_LOG':app_log,
                 'TEST_PG_RC':str(pg_rc),'TEST_APP_RC':str(app_rc),'TEST_EXPECT_PG':'lab-db' if stage=='source' else 'restore-db'}
            script='''set -euo pipefail
sudo(){ "$@"; }
stack(){ [[ "$*" == 'logs --no-color api web bootstrap ingress idp' ]] || return 99; printf '%s' "$TEST_APP_LOG"; return "$TEST_APP_RC"; }
compose(){ [[ "$*" == "logs --no-color $TEST_EXPECT_PG" ]] || return 99; printf '%s' "$TEST_PG_LOG"; return "$TEST_PG_RC"; }
'''+FUNCTION+'\nscan_lab_logs "$1"\n'
            result=subprocess.run(['bash','-c',script,'test',stage],env=env,capture_output=True,text=True,timeout=10)
            receipts=[json.loads(line.removeprefix('F3_LAB_LOG_GUARD ')) for line in result.stdout.splitlines() if line.startswith('F3_LAB_LOG_GUARD ')]
            self.assertNotIn(SECRET,result.stdout+result.stderr)
            return result,receipts
    def test_both_log_groups_source(self):
        r,x=self.run_pipeline();self.assertEqual(r.returncode,0);self.assertEqual([a['service_group'] for a in x],['app','postgres']);self.assertTrue(all(a['result']=='NO_LITERAL_MATCHES' for a in x))
    def test_restore_db_selected(self):
        r,x=self.run_pipeline(stage='restore');self.assertEqual(r.returncode,0);self.assertEqual([a['stage'] for a in x],['restore','restore'])
    def test_pg_leak_fails(self):
        r,x=self.run_pipeline(pg_log=SECRET);self.assertNotEqual(r.returncode,0);self.assertEqual(x[-1]['result'],'LEAK_FOUND')
    def test_empty_pg_fails(self):
        r,x=self.run_pipeline(pg_log='');self.assertNotEqual(r.returncode,0);self.assertEqual(x[-1]['result'],'INCOMPLETE_EMPTY_LOG')
    def test_pg_collection_failure_cannot_pass_pipeline(self):
        r,x=self.run_pipeline(pg_rc=19);self.assertNotEqual(r.returncode,0)
    def test_app_leak_stops_before_pg(self):
        r,x=self.run_pipeline(app_log=SECRET);self.assertNotEqual(r.returncode,0);self.assertEqual(len(x),1);self.assertEqual(x[0]['result'],'LEAK_FOUND')
    def test_app_collection_failure_stops(self):
        r,x=self.run_pipeline(app_rc=19);self.assertNotEqual(r.returncode,0);self.assertEqual(len(x),1)

if __name__=='__main__': unittest.main()
