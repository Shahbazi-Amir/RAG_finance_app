"""Existing product.v1 privacy wire checks only; no policy or endpoint is enabled."""
import copy,json,unittest
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker

ROOT=Path(__file__).resolve().parents[3]
SCHEMA=json.loads((ROOT/"packages/contracts/product.v1.schema.json").read_text())
VALIDATOR=Draft202012Validator(SCHEMA,format_checker=FormatChecker())
STAMP="2026-11-25T00:00:00Z"
def command(scope="conversation"):
    return dict(kind="delete_command",contract_version="product.v1",deletion_scope=scope,
                conversation_id="fixture-conversation" if scope=="conversation" else None,
                confirmed_by_user=True,client_action_id="fixture-action")
def status():
    return dict(kind="delete_status",contract_version="product.v1",deletion_request_id="fixture-operation",
                owner_user_id="fixture-owner",request_id="fixture-request",trace_id="fixture-trace",
                deletion_scope="conversation",conversation_id="fixture-conversation",state="processing",
                backend_confirmed=False,requested_at=STAMP,completed_at=None,error=None,client_action_id="fixture-action")
def feedback():
    return dict(kind="feedback_submit_request",contract_version="product.v1",client_feedback_id="fixture-feedback",
                conversation_id="fixture-conversation",answer_id="fixture-answer",rating="positive",reason=None,
                idempotency_key="fixture-feedback-key")
def receipt():
    return dict(kind="feedback_submit_receipt",contract_version="product.v1",client_feedback_id="fixture-feedback",
                conversation_id="fixture-conversation",answer_id="fixture-answer",idempotency_key="fixture-feedback-key",
                idempotency_scope="trusted_user+submit_feedback+answer",owner_user_id="fixture-owner",
                request_id="fixture-request",trace_id="fixture-trace",payload_sha256="a"*64,
                disposition="replayed",feedback_id="fixture-stored-feedback",persisted_at=STAMP,error=None)
class Tests(unittest.TestCase):
    def valid(self,value):self.assertTrue(VALIDATOR.is_valid(value))
    def invalid(self,value):self.assertFalse(VALIDATOR.is_valid(value))
    def test_account_and_conversation_delete_commands(self):
        self.valid(command());self.valid(command("account"))
    def test_confirmation_required_not_proof(self):
        self.invalid(dict(command(),confirmed_by_user=False))
        self.invalid(dict(command(),backend_confirmed=True))
    def test_delete_scope_binding(self):
        self.invalid(dict(command(),conversation_id=None))
        self.invalid(dict(command("account"),conversation_id="fixture-conversation"))
    def test_server_owned_identifiers_not_client_input(self):
        for value in (command(),feedback()):
            for key in ("owner_user_id","request_id","trace_id"):
                with self.subTest(kind=value["kind"],key=key):
                    self.invalid(dict(value,**{key:"fixture-forged"}))
    def test_status_pending_is_not_success(self):
        self.valid(status())
        self.invalid(dict(status(),backend_confirmed=True))
        self.invalid(dict(status(),completed_at=STAMP))
    def test_completed_requires_server_confirmation(self):
        self.valid(dict(status(),state="succeeded",backend_confirmed=True,completed_at=STAMP))
        self.invalid(dict(status(),state="succeeded",completed_at=STAMP))
        self.invalid(dict(status(),state="succeeded",backend_confirmed=True))
    def test_unknown_is_not_server_status(self):
        self.invalid(dict(status(),state="unknown"))
    def test_status_query_not_owner_assertion(self):
        q=dict(kind="delete_status_query",contract_version="product.v1",deletion_request_id="fixture-operation",client_action_id="fixture-action")
        self.valid(q)
        self.invalid(dict(q,owner_user_id="fixture-forged"))
    def test_feedback_rating_reason_and_retry_shape(self):
        self.valid(feedback());self.valid(dict(feedback(),rating="negative",reason="synthetic"))
        self.invalid(dict(feedback(),rating="other"))
        self.invalid(dict(feedback(),reason="x"*501))
        self.invalid(dict(feedback(),idempotency_key="short"))
    def test_feedback_receipt_not_fake_persistence(self):
        self.valid(receipt())
        self.invalid(dict(receipt(),feedback_id=None))
        self.invalid(dict(receipt(),persisted_at=None))
        self.invalid(dict(receipt(),idempotency_scope="global"))
    def test_no_version_bypass(self):
        for value in (command(),status(),feedback(),receipt()):
            self.invalid(dict(value,contract_version="product.v2"))
if __name__=="__main__":unittest.main()
