from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.phase3.rag_runtime.arvan_live_dispatch import ArvanLiveDispatch, LiveAnswerStore, public_result
from src.phase3.rag_runtime.arvan_turn_policy import DailyQuota, QuotaExceeded, ResponseCache, account_key
from src.phase3.rag_runtime.dispatch_claim_bridge import CommittedDispatchPermit
from src.phase3.rag_runtime.staging_invited_result_fixture import InvitedBinding
from src.phase3.rag_runtime.staging_preflight import AttemptBinding


ANSWER = {"outcome": "ANSWER", "issues": [], "claims": [
    {"text": "سواد مالی", "citation": {"quote": "شاهد مالی", "chunk_id": "fixture"}}
]}


def test_isolated_turns_and_follow_up_rewrite():
    with TemporaryDirectory() as folder:
        store = LiveAnswerStore(Path(folder))
        binding = InvitedBinding("owner", "a" * 64, 0, 1, None, "chat",
                                 "client", "key12345", "b" * 32, "c" * 32, "d" * 32)
        store.save(binding, "q1", public_result(ANSWER), ANSWER)
        assert store.answered_messages("owner", "chat") == ["q1"]
        assert store.answered_messages("other", "chat") == []
        assert store.answered_messages("owner", "other") == []

        turns = ({"question": "سواد مالی چیست؟", "answer": "سواد مالی"},)
        rewrite = Mock(return_value="سواد مالی چه فایده‌ای دارد؟")
        generate = Mock(return_value=ANSWER)
        service = ArvanLiveDispatch(Path("/unused"), generate, store, rewrite=rewrite)
        service._exchange = Mock(side_effect=lambda req, timeout: {
            "attempt_id": req["attempt_id"], "source": {"question": req["question"]}})
        second = replace(binding, attempt_id="e" * 32)
        permit = CommittedDispatchPermit("owner", AttemptBinding(
            second.attempt_id, second.attempt_request_id, second.attempt_trace_id), uuid4())
        assert service.slots.acquire(blocking=False)
        service.enqueue(permit, second, "خب بیشتر توضیح بده", "q2", turns)
        service.generation.submit(lambda: None).result()
        service.retrieval.shutdown(wait=True)
        service.generation.shutdown(wait=True)
        rewrite.assert_called_once_with("خب بیشتر توضیح بده", turns)
        generate.assert_called_once_with({"question": "سواد مالی چه فایده‌ای دارد؟"}, second.attempt_id, turns)
        assert service.read(second, "q2")["outcome"] == "ANSWER"
        assert not service._shared_query("خب بیشتر توضیح بده", ())
        service.close()


def test_cache_expiry_version_normalization_and_thread_exclusion():
    with TemporaryDirectory() as folder:
        now = [100]
        cache = ResponseCache(Path(folder), 7, "worker-a", clock=lambda: now[0])
        cache.save("سواد مالی چیست؟", ANSWER, contextual=False)
        assert cache.read("  سواد  مالی چیست؟ ", contextual=False) == ANSWER
        assert cache.read("سواد مالی چیست؟", contextual=True) is None
        cache.save("خب بیشتر توضیح بده", ANSWER, contextual=True)
        assert cache.read("خب بیشتر توضیح بده", contextual=False) is None
        for result in ({**ANSWER, "issues": ["REVIEW"]}, {**ANSWER, "outcome": "NO_ANSWER"}):
            cache.save("پرسش دیگر", result, contextual=False)
        assert cache.read("پرسش دیگر", contextual=False) is None
        assert ResponseCache(Path(folder), 7, "worker-b", clock=lambda: now[0]).read(
            "سواد مالی چیست؟", contextual=False) is None
        now[0] += 7
        assert cache.read("سواد مالی چیست؟", contextual=False) is None
        assert cache.path.stat().st_mode & 0o777 == 0o600


def test_quota_replay_persistence_exemption_and_tehran_midnight():
    def send(i):
        return {"requested_conversation_id": None, "client_message_id": str(i),
                "idempotency_key": "fixture"}
    now = [datetime(2026, 11, 26, 20, 29, 59, tzinfo=timezone.utc).timestamp()]
    vip = account_key("vip@example.invalid")
    policy = lambda: (20, {vip: None})
    with TemporaryDirectory() as folder:
        quota = DailyQuota(Path(folder), policy, clock=lambda: now[0])
        for i in range(20):
            quota.reserve("owner", (), send(i))
            quota.reserve("vip-owner", (vip,), send(i))
        quota.reserve("owner", (), send(0))
        quota.reserve("vip-owner", (vip,), send(20))
        assert quota.read("vip-owner", (vip,)) == {"limit": None, "remaining": None}
        quota = DailyQuota(Path(folder), policy, clock=lambda: now[0])
        with pytest.raises(QuotaExceeded) as denied:
            quota.reserve("owner", (), send(20))
        assert denied.value.quota == {"limit": 20, "remaining": 0}
        assert quota.read("other", ())["remaining"] == 20
        now[0] += 1
        assert quota.read("owner", ())["remaining"] == 20
        assert quota.path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("aliases", [("blocked",), ("unlimited", "standard", "blocked")])
def test_zero_quota_override_is_most_restrictive(tmp_path, aliases):
    quota = DailyQuota(tmp_path, lambda: (20, {"blocked": 0, "standard": 3, "unlimited": None}))
    assert quota.read("owner", aliases) == {"limit": 0, "remaining": 0}
    payload = {"requested_conversation_id": None, "client_message_id": "fixture",
               "idempotency_key": "fixture"}
    with pytest.raises(QuotaExceeded) as denied:
        quota.reserve("owner", aliases, payload)
    assert denied.value.quota == {"limit": 0, "remaining": 0}
    assert quota.read("other", ()) == {"limit": 20, "remaining": 20}


def test_live_api_exhaustion_response_is_429_without_retry(monkeypatch):
    from fastapi.testclient import TestClient
    from apps.api import product_session_api as api

    monkeypatch.setenv("API_RUNNER_EXECUTION_MODE", "LIVE_DISPATCH")
    quota = {"limit": 20, "remaining": 0}
    send = Mock(side_effect=QuotaExceeded(quota))
    monkeypatch.setattr(api, "_run_arvan_send", send)
    payload = {"kind": "send_message_request", "contract_version": "product.v1",
               "requested_conversation_id": None, "client_message_id": "question",
               "idempotency_key": "test12345", "question": "سواد مالی چیست؟"}
    response = TestClient(api.app).post("/v1/messages", json=payload)
    assert response.status_code == 429
    assert response.json() == {"code": "DAILY_QUOTA_EXCEEDED", "daily_quota": quota}
    assert response.headers["cache-control"] == "no-store"
    send.assert_called_once()


def test_cache_hit_persists_new_turn_without_retrieval_or_provider():
    with TemporaryDirectory() as folder:
        path = Path(folder)
        generate = Mock()
        worker = Mock()
        binding = InvitedBinding("second-owner", "a" * 64, 0, 1, None, "new-chat",
                                 "client", "key12345", "b" * 32, "c" * 32, "d" * 32)
        service = ArvanLiveDispatch(path / "unused", generate, LiveAnswerStore(path))
        service._exchange = worker
        service.cache = ResponseCache(path, 604800, "worker-a")
        service.cache.save("سواد مالی چیست؟", ANSWER, contextual=False)
        permit = CommittedDispatchPermit("second-owner", AttemptBinding(
            binding.attempt_id, binding.attempt_request_id, binding.attempt_trace_id), uuid4())
        try:
            assert service.slots.acquire(blocking=False)
            service.enqueue(permit, binding, "سواد مالی چیست؟", "new-question")
            assert service.read(binding, "new-question") == public_result(ANSWER)
            assert service.history("second-owner", "new-chat", ["new-question"]) == {
                "new-question": public_result(ANSWER)}
            worker.assert_not_called()
            generate.assert_not_called()
        finally:
            service.close()


@pytest.mark.parametrize("text", [
    "سلام", "سلام چه طوری؟", "سلام چطوری؟", "خوبی؟", "مرسی", "ممنون",
    "تو کی هستی؟ چه کمکی می‌تونی بکنی؟",
])
def test_pure_social_turn_gets_fast_persian_reply(text):
    from src.phase3.rag_runtime.arvan_live_dispatch import conversational_reply

    reply = conversational_reply(text)
    assert reply and "سواد مالی" in reply and "شواهد" not in reply


@pytest.mark.parametrize("text", [
    "سلام، سود مرکب چطور محاسبه می‌شود؟", "ممنون، اگر بدهی دارم چه کنم؟",
    "چه کمکی برای بودجه‌بندی می‌تونی بکنی؟", "خب بیشتر توضیح بده",
])
def test_financial_and_follow_up_turns_remain_grounded(text):
    from src.phase3.rag_runtime.arvan_live_dispatch import conversational_reply

    assert conversational_reply(text) is None


def test_social_reply_with_thread_is_durable_and_bypasses_provider_and_cache():
    with TemporaryDirectory() as folder:
        path = Path(folder)
        binding = InvitedBinding("owner", "a" * 64, 0, 1, None, "chat",
                                 "client", "key12345", "b" * 32, "c" * 32, "d" * 32)
        store = LiveAnswerStore(path)
        service = ArvanLiveDispatch(path / "worker", Mock(), store, rewrite=Mock())
        service._exchange = Mock()
        service.cache = Mock()
        permit = CommittedDispatchPermit("owner", AttemptBinding(
            binding.attempt_id, binding.attempt_request_id, binding.attempt_trace_id), uuid4())
        try:
            assert service.slots.acquire(blocking=False)
            service.enqueue(permit, binding, "سلام چه طوری؟", "msg", ({"question": "مالی"},))
            result = service.read(binding, "msg")
            assert result["outcome"] == "CONVERSATIONAL"
            assert result["claims"] == []
            assert "مشاور مالی" in result["reply"]
            assert store.read("owner", "chat", ["msg"])["msg"][1] == result
            assert store.answered_messages("owner", "chat") == []
            assert service.cache.mock_calls == []
            service.generate.assert_not_called()
            service.rewrite.assert_not_called()
            service._exchange.assert_not_called()
        finally:
            service.close()
