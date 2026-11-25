import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/phase3'))
from f3_policy_rehearsal import incident_plan,backup_rotation_preview,Denied
OBS={'dependency_503':True,'recovered':True,'cross_owner_exposure':False,'suspected_secret':False,'replay_duplicate':False,'backup_corrupt':False,'unknown_result':False}
P={'mode':'SYNTHETIC_PLAN_ONLY','approved':False,'keep_latest':2,'age_days':30}
NOW='2026-11-25T00:00:00Z'
def record(n,date,**kw):return {'id':'synthetic-'+str(n),'created_at':date,'verified':True,'encrypted':True,'hold':False,'sha256':format(n,'064x'),**kw}
R=[record(1,'2026-09-01T00:00:00Z'),record(2,'2026-10-01T00:00:00Z',hold=True),record(3,'2026-11-24T00:00:00Z'),record(4,'2026-11-23T00:00:00Z'),record(5,'2026-10-01T00:00:00Z',verified=False)]
class Tests(unittest.TestCase):
 def test_dependency_recovered(self):
  r=incident_plan(OBS);self.assertEqual(r['issues'][0]['category'],'DEPENDENCY_UNAVAILABLE');self.assertIn('REVIEW_RECOVERY_OBSERVATION',r['issues'][0]['suggested_actions']);self.assertFalse(r['approved'])
 def test_unknown_never_replays(self):
  r=incident_plan({**OBS,'unknown_result':True});self.assertIn('NO_AUTOMATIC_REPLAY',r['issues'][-1]['suggested_actions'])
 def test_multi_incident(self):
  r=incident_plan({k:True for k in OBS});self.assertEqual(len(r['issues']),6);self.assertTrue(all(x['response_sla_approved'] is None for x in r['issues']))
 def test_not_recovered(self):self.assertIn('KEEP_UNAVAILABLE',incident_plan({**OBS,'recovered':False})['issues'][0]['suggested_actions'])
 def test_unknown_field_denied(self):
  with self.assertRaises(Denied):incident_plan({**OBS,'raw_password':'canary'})
 def test_bool_type_denied(self):
  with self.assertRaises(Denied):incident_plan({**OBS,'dependency_503':1})
 def test_backup_preview(self):
  r=backup_rotation_preview(R,P,NOW);d={x['id']:x['decision'] for x in r['decisions']};self.assertEqual(d['synthetic-1'],'REVIEW_ELIGIBLE_IN_SIMULATION_ONLY');self.assertEqual(d['synthetic-2'],'KEEP_HOLD');self.assertEqual(d['synthetic-3'],'KEEP_LATEST_VERIFIED');self.assertEqual(d['synthetic-4'],'KEEP_LATEST_VERIFIED');self.assertEqual(d['synthetic-5'],'QUARANTINE_REVIEW_NO_DELETE');self.assertEqual(r['delete_commands'],[])
 def test_approved_flag_refused(self):self.bad_policy({'approved':True})
 def test_production_refused(self):self.bad_policy({'mode':'PRODUCTION'})
 def test_zero_keep_refused(self):self.bad_policy({'keep_latest':0})
 def test_zero_age_refused(self):self.bad_policy({'age_days':0})
 def test_duplicate_refused(self):
  with self.assertRaises(Denied):backup_rotation_preview(R+[R[0]],P,NOW)
 def test_future_refused(self):
  with self.assertRaises(Denied):backup_rotation_preview(R+[record(6,'2027-01-01T00:00:00Z')],P,NOW)
 def test_real_id_refused(self):
  with self.assertRaises(Denied):backup_rotation_preview([{**R[0],'id':'prod-volume'}],P,NOW)
 def test_path_refused(self):
  with self.assertRaises(Denied):backup_rotation_preview([{**R[0],'path':'/private/data'}],P,NOW)
 def test_bad_digest(self):
  with self.assertRaises(Denied):backup_rotation_preview([{**R[0],'sha256':'bad'}],P,NOW)
 def test_invalid_utc(self):
  with self.assertRaises(Denied):backup_rotation_preview(R,P,'2026-11-25')
 def bad_policy(self,edit):
  with self.assertRaises(Denied):backup_rotation_preview(R,{**P,**edit},NOW)
if __name__=='__main__':unittest.main(verbosity=2)
