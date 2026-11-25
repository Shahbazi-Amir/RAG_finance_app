#!/usr/bin/env python3
"""Pure, proposal-only incident and backup rotation planner. Never deletes or deploys."""
from datetime import datetime, timezone, timedelta
import re
class Denied(ValueError):pass

def need(ok,code):
    if not ok:raise Denied(code)

def incident_plan(observation):
    keys={'dependency_503','recovered','cross_owner_exposure','suspected_secret','replay_duplicate','backup_corrupt','unknown_result'}
    need(type(observation) is dict and set(observation)==keys and all(type(x) is bool for x in observation.values()),'INCIDENT_SCHEMA')
    issues=[]
    def add(key,role,actions):issues.append({'category':key,'owner_role_proposed':role,'suggested_actions':actions,'severity_approved':None,'response_sla_approved':None})
    if observation['cross_owner_exposure']:add('PRIVACY_BOUNDARY','Security/DB',['HOLD','PRESERVE_SANITIZED_EVIDENCE','REQUEST_SECURITY_OWNER'])
    if observation['suspected_secret']:add('SECRET_FINDING','Security',['HOLD','RESTRICT_RECEIPTS','REQUEST_TRIAGE_NO_AUTOMATIC_WAIVER'])
    if observation['replay_duplicate']:add('DURABLE_DUPLICATE','API/DB',['HOLD','CHECK_TRANSACTION_RECEIPTS','NO_AUTOMATIC_REPLAY'])
    if observation['backup_corrupt']:add('BACKUP_INTEGRITY','DB/Ops',['HOLD','QUARANTINE_UNVERIFIED_BACKUP','NO_RESTORE'])
    if observation['dependency_503']:add('DEPENDENCY_UNAVAILABLE','Ops',['HOLD','VERIFY_BOTH_OWNER_READINESS','REVIEW_RESTORED_STATE']+(['REVIEW_RECOVERY_OBSERVATION'] if observation['recovered'] else ['KEEP_UNAVAILABLE']))
    if observation['unknown_result']:add('UNKNOWN_RESULT','API/Ops',['HOLD','GET_ONLY_RECONCILIATION','NO_AUTOMATIC_REPLAY'])
    return {'schema':'foundation.f3.incident_proposal.v1','issues':issues,'release':'HOLD','approved':False,'human_tabletop_completed':False,'external_action':False}

def utc(value):
    need(isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',value) is not None,'UTC_REQUIRED')
    try:return datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:raise Denied('UTC_INVALID') from None

def backup_rotation_preview(records,policy,as_of):
    # Explicit synthetic simulation only: no filesystem path, no execution, no
    # retention default or policy on user History. Unknown input fails closed.
    need(type(policy) is dict and set(policy)=={'mode','approved','keep_latest','age_days'} and policy['mode']=='SYNTHETIC_PLAN_ONLY' and policy['approved'] is False,'POLICY_NOT_SYNTHETIC')
    k,d=policy['keep_latest'],policy['age_days'];need(type(k) is int and 1<=k<=100 and type(d) is int and 1<=d<=3650,'POLICY_BOUNDS')
    now=utc(as_of);need(type(records) is list and 1<=len(records)<=1000,'BACKUP_COUNT')
    seen=set();rows=[]
    for record in records:
        need(type(record) is dict and set(record)=={'id','created_at','verified','encrypted','hold','sha256'},'BACKUP_SCHEMA')
        rid=record['id'];need(isinstance(rid,str) and re.fullmatch(r'synthetic-[a-z0-9-]{1,64}',rid) and rid not in seen,'BACKUP_ID')
        seen.add(rid);need(all(type(record[x]) is bool for x in ('verified','encrypted','hold')),'BACKUP_FLAGS')
        need(isinstance(record['sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',record['sha256']),'BACKUP_DIGEST')
        t=utc(record['created_at']);need(t<=now,'FUTURE_BACKUP');rows.append((t,rid,record))
    valid=sorted([x for x in rows if x[2]['verified'] and x[2]['encrypted']],reverse=True)
    protected={x[1] for x in valid[:k]}
    out=[]
    for t,rid,r in sorted(rows):
        if r['hold']:decision='KEEP_HOLD'
        elif not r['verified'] or not r['encrypted']:decision='QUARANTINE_REVIEW_NO_DELETE'
        elif rid in protected:decision='KEEP_LATEST_VERIFIED'
        elif now-t<timedelta(days=d):decision='KEEP_WITHIN_EXAMPLE_AGE'
        else:decision='REVIEW_ELIGIBLE_IN_SIMULATION_ONLY'
        out.append({'id':rid,'decision':decision})
    return {'schema':'foundation.f3.synthetic_backup_rotation_preview.v1','scope':'NO_REAL_BACKUP_OR_USER_DATA','approved':False,'delete_commands':[],'deletion_performed':False,'decisions':out}
