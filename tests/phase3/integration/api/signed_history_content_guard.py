"""Real signed browser content guard; synthetic inputs in disposable CI only.

Mix into the existing #129 real OIDC/SQL/Restore journey. No interception,
forged session, owner header, engine, migration, or product policy change.
"""
from __future__ import annotations

SENTINEL = "__f3_history_content_executed"
TITLE = 'آزمون RTL <svg onload="window.__f3_history_content_executed=1"></svg>'
BODY = ('پیام آزمایشی RTL / ABC-123 <img src="data:," '
        'onerror="window.__f3_history_content_executed=1"> '
        '<script>window.__f3_history_content_executed=1</script>')
ACTIVE = 'script,svg,img,iframe,object,embed,link,style,form,[onload],[onerror]'


async def assert_content_dom(page, cid, mid, title, body, foreign_body):
    """Check actual rendered text, scoped DOM, execution flag, and isolation."""
    assert foreign_body and foreign_body != body, 'INVALID_FOREIGN_FIXTURE'
    title_node = page.get_by_test_id('conversation-' + cid).locator('.nav-thread-text')
    message_node = page.get_by_test_id('history-message-' + mid)
    assert await title_node.count() == 1, 'TITLE_CARD_NOT_UNIQUE'
    assert await message_node.count() == 1, 'MESSAGE_CARD_NOT_UNIQUE'
    assert await title_node.text_content() == title, 'TITLE_NOT_LITERAL'
    assert await message_node.locator('.history-message-text').count() == 1, 'MESSAGE_TEXT_NOT_UNIQUE'
    assert await message_node.locator('.history-message-text').text_content() == body, 'BODY_NOT_LITERAL'
    assert await title_node.locator(ACTIVE).count() == 0, 'ACTIVE_MARKUP_IN_TITLE'
    assert await message_node.locator(ACTIVE).count() == 0, 'ACTIVE_MARKUP_IN_BODY'
    assert await page.evaluate('(name) => !Object.prototype.hasOwnProperty.call(window, name)', SENTINEL), 'CONTENT_EXECUTED'
    assert foreign_body not in await page.locator('main.history-shell').inner_text(), 'FOREIGN_BODY_VISIBLE'


class SignedContentGuardMixin:
    """Use real synthetic DB rows as inputs, and existing signed reads as outputs."""

    def seed_extra(self, label):
        if label != 'A':
            result = super().seed_extra(label)
            if label == 'B':
                self.guard_foreign_cid = result[0]
                self.guard_foreign_body = result[2]
            return result
        import os
        import uuid
        import psycopg
        from psycopg.rows import dict_row
        from apps.api import history_api

        owner = self.owners[label]
        request = {'kind': 'create_conversation_request', 'contract_version': 'product.v1',
                   'client_conversation_id': history_api.uid(),
                   'idempotency_key': 'browser_' + uuid.uuid4().hex, 'title': TITLE}
        # Same role, transaction and entrypoint as the parent synthetic seed.
        with psycopg.connect(os.environ['DB_APP_DSN'], autocommit=True,
                             row_factory=dict_row) as db:
            receipt = history_api.create_conversation(db, owner, request,
                                                      history_api.uid(), history_api.uid())
        cid = receipt['conversation']['conversation_id']
        mid = history_api.uid()
        with psycopg.connect(os.environ['DB_MIG_DSN'], autocommit=True) as db:
            db.execute('INSERT INTO history_l1.messages '
                       '(owner_id,id,conversation_id,role,body) VALUES (%s,%s,%s,\'user\',%s)',
                       (owner, mid, cid, BODY))
        self.guard_cid, self.guard_mid = cid, mid
        return cid, mid, BODY

    async def verify_31_message_page2(self, page, conversation_id, rows, expected_owner):
        await super().verify_31_message_page2(page, conversation_id, rows, expected_owner)
        assert conversation_id == self.guard_cid, 'GUARD_WRONG_CONVERSATION'
        matches = [r for r in rows if r['id'] == self.guard_mid]
        assert len(matches) == 1 and matches[0]['body'] == BODY, 'GUARD_SQL_FIXTURE_DRIFT'
        await assert_content_dom(page, self.guard_cid, self.guard_mid, TITLE, BODY,
                                 self.guard_foreign_body)
        self.content_guard_witnesses = getattr(self, 'content_guard_witnesses', 0) + 1
        print('F3_SIGNED_LITERAL_TITLE_BODY_NO_ACTIVE_MARKUP_NO_FOREIGN_BODY_PASS', flush=True)

    async def verify_browser_privacy(self, browser, a, b, raw_a, raw_b, aid, message):
        await super().verify_browser_privacy(browser, a, b, raw_a, raw_b, aid, message)
        # Symmetric real session-only foreign reads, no injected owner headers.
        before = self.counts()
        for page, cid, foreign_body in ((a, self.guard_foreign_cid, self.guard_foreign_body),
                                         (b, self.guard_cid, BODY)):
            result = await page.evaluate("""async id => {
                const r=await fetch('/api/history/conversations/'+id+'/messages?limit=2',
                                    {cache:'no-store'});
                return {status:r.status,cache:r.headers.get('cache-control'),body:await r.text()};
            }""", cid)
            assert result['status'] == 404 and result['cache'] == 'no-store'
            assert foreign_body not in result['body'] and cid not in result['body']
        assert self.counts() == before
        print('F3_SIGNED_SYMMETRIC_FOREIGN_CONTENT_DENIED_NO_WRITES_PASS', flush=True)
