"""Separate synthetic Keycloak realm: verify configured password hash and lockout.

This does NOT change the product login realm, publish credentials, prescribe
production password/lockout policy, or call a target/engine. Actual Keycloak
admin/Code+S256 form path; no mock IdP. Only fixed counts and metadata leave CI.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from collections import Counter
import httpx

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/"tests/phase3/integration/api")]
from initial_oidc_harness import DisposableKeycloak,IsolatedOIDCFailure

class SecurityRealm(DisposableKeycloak):
    def __init__(self):
        super().__init__()
        self.REALM="f3-security-only-"+secrets.token_hex(6)
        self.CLIENT_ID=self.REALM

def ensure(ok,code):
    if not ok:raise RuntimeError(code)

def execute():
    ensure(os.getenv("CI")=="true" and os.getenv("GITHUB_ACTIONS")=="true"
           and os.getenv("RUNNER_ENVIRONMENT")=="github-hosted"
           and os.getenv("GITHUB_REF")=="refs/heads/integration/f3-foundation-send-fence-restore-20261124",
           "DISPOSABLE_CI_ONLY")
    ensure(not any(os.getenv(k) for k in ("DOCKER_HOST","DOCKER_CONTEXT","COMPOSE_FILE","COMPOSE_PROFILES")),
           "UNEXPECTED_DOCKER_CONTEXT")
    kc=SecurityRealm()
    try:
        kc.start()
        ensure(re.fullmatch(r"f3-security-only-[a-f0-9]{12}",kc.REALM) is not None,"WRONG_REALM")
        root=kc.base+"/admin/realms/"+kc.REALM
        with httpx.Client(trust_env=False,timeout=20,follow_redirects=False) as c:
            auth=c.post(kc.base+"/realms/master/protocol/openid-connect/token",
                        data={"grant_type":"password","client_id":"admin-cli","username":"ci-bootstrap",
                              "password":kc.password})
            ensure(auth.status_code==200,"ADMIN_BOOTSTRAP_DENIED")
            token=auth.json()["access_token"]
            headers={"Authorization":"Bearer "+token}
            def get(suffix="",**kw):
                r=c.get(root+suffix,headers=headers,**kw)
                ensure(r.status_code==200,"KEYCLOAK_ADMIN_READ_FAILED")
                return r.json()
            def put(suffix,doc):
                r=c.put(root+suffix,headers=headers,json=doc)
                ensure(r.status_code==204,"KEYCLOAK_ADMIN_WRITE_FAILED")
            def clear(label):
                sub=kc.accounts[label]["sub"]
                r=c.delete(root+"/attack-detection/brute-force/users/"+sub,headers=headers)
                ensure(r.status_code==204,"KEYCLOAK_CLEAR_FAILED")
            # Explicit lab-only values. Not a suggestion for product policy.
            policy="hashAlgorithm(pbkdf2-sha512) and hashIterations(210000)"
            realm=get()
            ensure(realm["realm"]==kc.REALM and realm.get("bruteForceProtected") is False,"UNEXPECTED_REALM")
            realm.update(passwordPolicy=policy,bruteForceProtected=True,permanentLockout=False,
                         failureFactor=2,waitIncrementSeconds=60,maxFailureWaitSeconds=60,
                         minimumQuickLoginWaitSeconds=0,quickLoginCheckMilliSeconds=0,
                         maxDeltaTimeSeconds=300,eventsEnabled=True,eventsExpiration=600,
                         enabledEventTypes=["LOGIN","LOGIN_ERROR"],eventsListeners=[])
            put("",realm)
            configured=get()
            ensure(configured.get("bruteForceProtected") is True and configured.get("permanentLockout") is False
                   and configured.get("failureFactor")==2 and configured.get("eventsEnabled") is True,
                   "LAB_POLICY_NOT_APPLIED")
            ensure(configured.get("passwordPolicy")==policy,"LAB_HASH_POLICY_NOT_APPLIED")
            metadata=[]
            for label,user in kc.accounts.items():
                # Apply policy through actual password reset on test-only
                # principals. Password stays in RAM; never print body.
                fresh="Az9!"+secrets.token_urlsafe(28)
                put("/users/"+user["sub"]+"/reset-password",
                    {"type":"password","value":fresh,"temporary":False})
                user["password"]=fresh
                creds=get("/users/"+user["sub"]+"/credentials")
                passwords=[x for x in creds if x.get("type")=="password"]
                ensure(len(passwords)==1,"EXPECTED_ONE_PASSWORD_CREDENTIAL")
                entry=passwords[0]
                data=entry.get("credentialData")
                ensure(isinstance(data,str),"MISSING_CREDENTIAL_METADATA")
                details=json.loads(data)
                ensure(details.get("algorithm")=="pbkdf2-sha512" and details.get("hashIterations")==210000,
                       "ACTUAL_HASH_METADATA_MISMATCH")
                ensure(fresh not in json.dumps(entry),"RAW_PASSWORD_EXPOSED")
                ensure(not entry.get("secretData"),"ADMIN_PASSWORD_HASH_EXPOSED")
                metadata.append({"algorithm":details["algorithm"],"iterations":details["hashIterations"],
                                 "raw_password_and_secret_data_not_returned":True})
            def attempt(label,wrong=False):
                user=kc.accounts[label];original=user["password"]
                if wrong:user["password"]="WrongAz9!"+secrets.token_urlsafe(28)
                try:
                    try:
                        _,callback=kc.actual_login_callback(label)
                    except IsolatedOIDCFailure:
                        return False
                    return "code" in callback and len(callback["code"])==1 and "error" not in callback
                finally:user["password"]=original
            def state(label):
                return get("/attack-detection/brute-force/users/"+kc.accounts[label]["sub"])
            ensure(attempt("A") and attempt("B"),"VALID_INITIAL_FORM_DENIED")
            for _ in range(2):
                ensure(not attempt("A",True),"WRONG_PASSWORD_ACCEPTED")
            # Poll the native attack-detection state, not merely the text
            # of a browser error page or a local mock counter.
            for _ in range(50):
                a=state("A")
                if a.get("disabled") is True and a.get("numFailures",0)>=2:break
                time.sleep(.2)
            else:raise RuntimeError("NATIVE_TEMP_LOCKOUT_NOT_OBSERVED")
            ensure(not attempt("A"),"LOCKED_ACCOUNT_CORRECT_PASSWORD_ACCEPTED")
            ensure(attempt("B"),"INDEPENDENT_ACCOUNT_IMPACTED")
            ensure(state("B").get("disabled") is not True,"INDEPENDENT_ACCOUNT_LOCKED")
            clear("A")
            for _ in range(50):
                if not state("A").get("disabled",False):break
                time.sleep(.2)
            else:raise RuntimeError("LAB_LOCKOUT_CLEAR_NOT_OBSERVED")
            ensure(attempt("A"),"CLEARED_ACCOUNT_NOT_RECOVERED")
            events=get("/events",params={"max":100})
            event_counts=Counter(e.get("type") for e in events)
            ensure(event_counts["LOGIN"]>=4 and event_counts["LOGIN_ERROR"]>=3,"NATIVE_LOGIN_EVENTS_MISSING")
            # Native IdP event storage is inspected in memory only. Do
            # not upload IDs, IPs, email, token, Code, raw event or logs.
            raw=json.dumps(events)
            for secret in (token,kc.password,*[u["password"] for u in kc.accounts.values()]):
                ensure(secret not in raw,"NATIVE_EVENT_SECRET_LEAK")
            image=json.loads(kc.docker("inspect",kc.container,capture=True))[0]["Image"]
            ensure(re.fullmatch(r"sha256:[0-9a-f]{64}",image) is not None,"IDP_IMAGE_ID_MISSING")
            receipt={"schema":"foundation.f3.disposable_idp_security.v1","source_sha":os.environ["GITHUB_SHA"],
                     "run_id":os.environ["GITHUB_RUN_ID"],"idp_image":kc.IMAGE,"local_image_id":image,
                     "separate_synthetic_realm":True,"actual_password_credential_metadata":metadata,
                     "temporary_lockout_observed":True,"native_failure_count_at_least_two":True,
                     "locked_correct_password_denied":True,"other_account_unaffected":True,
                     "authorized_clear_and_form_login_recovered":True,
                     "native_idp_login_events":{k:event_counts[k] for k in ("LOGIN","LOGIN_ERROR")},
                     "raw_secrets_absent_from_scoped_event_storage":True,"raw_events_uploaded":False,
                     "product_login_realm_changed":False,"product_audit_implemented":False,
                     "production_password_policy_approved":False,"production_lockout_policy_approved":False,
                     "target_verified":False,"accepted":False}
            out=ROOT/"ci_receipts/f3_disposable_idp_security.json"
            out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(receipt,indent=2)+"\n")
            print("F3_DISPOSABLE_KEYCLOAK_HASH_LOCKOUT_NATIVE_LOGIN_EVENTS_PASS",flush=True)
    finally:kc.stop()

if __name__=="__main__":
    try:execute()
    except Exception as e:
        # Keep only the fixed locally defined diagnostic vocabulary. Do
        # not print exception strings from HTTP, JWT, SQL or subprocess.
        code=str(e) if isinstance(e,RuntimeError) and re.fullmatch(r"[A-Z0-9_]{1,80}",str(e)) else type(e).__name__
        print("F3_DISPOSABLE_IDP_SECURITY_FAILED:"+code,file=sys.stderr)
        raise SystemExit(1) from None
