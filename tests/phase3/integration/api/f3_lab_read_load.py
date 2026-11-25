"""Bounded GET-only browser witness, never a production load or SLO assertion.
Runs inside the already authenticated page. No cookie injection, no route mocks,
no mutation, no engine. Only aggregate durations and counts leave the page.
"""
import json
from f3_lab_http_metrics import percentiles

LIST_PATH = '/api/history/conversations'
TIERS = (1, 2, 4)
ROUNDS = 3
# Keep an explicit same-origin path; no caller-selected endpoint or redirect.
JS = r'''async ({role, owner, width, rounds, checkCursor, extraChecks=false}) => {
  const list = '/api/history/conversations';
  const detail = list + '/browser-a-1/messages?limit=30';
  const detailB = list + '/browser-b-1/messages?limit=30';
  const MAX_BYTES = 131072;
  const allowedReject = new Set([400,403,404,422]);
  const ids = role === 'a' ? ['browser-a-3','browser-a-2'] : ['browser-b-1'];
  const samples = [];
  const statuses = {};
  let cursor = null;
  async function boundedText(response) {
    if (!response.body || typeof response.body.getReader !== 'function') throw Error('body-stream');
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8',{fatal:true});
    let size=0, text='', complete=false;
    try {
      const length=response.headers.get('content-length');
      if (length !== null && (!/^\d+$/.test(length) || Number(length)>MAX_BYTES)) throw Error('body-limit');
      for (;;) {
        const {done,value}=await reader.read();
        if (done) { complete=true; break; }
        size+=value.byteLength;
        if (size>MAX_BYTES) throw Error('body-limit');
        text+=decoder.decode(value,{stream:true});
      }
      return text+decoder.decode();
    } finally {
      if (!complete) await reader.cancel().catch(()=>{});
      reader.releaseLock();
    }
  }
  async function read(path, kind) {
    const start = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const r = await fetch(path, {method:'GET', credentials:'same-origin',
        cache:'default', redirect:'error', signal:controller.signal});
      if (r.headers.get('cache-control') !== 'no-store') {
        if (r.body) await r.body.cancel().catch(()=>{});
        throw Error('cache');
      }
      const body = await boundedText(r);
      if (kind === 'negative') {
        if (!allowedReject.has(r.status) || body.includes('lab browser A') || body.includes('lab browser B') || body.includes('browser-msg-a') || body.includes('browser-msg-b')) throw Error('negative');
      } else if ((kind === 'detail' && role === 'b') || (kind === 'detail-b' && role === 'a')) {
        if (r.status !== 404 || ['lab browser A','lab browser B','browser-msg-a','browser-msg-b'].some(x=>body.includes(x))) throw Error('foreign');
      } else {
        if (r.status !== 200) throw Error('status');
        const d = JSON.parse(body);
        if (kind === 'list') {
          if (d.scope_user_id !== owner || JSON.stringify(d.items.map(x=>x.conversation_id)) !== JSON.stringify(ids)) throw Error('list-owner');
          if (role === 'a') {
            if (!d.page || !d.page.has_more || typeof d.page.next_cursor !== 'string' || !d.page.next_cursor) throw Error('cursor');
            cursor = d.page.next_cursor;
          }
        } else if (kind === 'next') {
          if (role !== 'a' || d.scope_user_id !== owner || JSON.stringify(d.items.map(x=>x.conversation_id)) !== JSON.stringify(['browser-a-1']) || !d.page || d.page.has_more !== false) throw Error('next-page');
        } else {
          const expected = kind === 'detail-b' ? [['browser-msg-b','lab browser B']] : [['browser-msg-a','lab browser A']];
          if (d.owner_user_id !== owner || JSON.stringify(d.items.map(x=>[x.message_id,x.text])) !== JSON.stringify(expected)) throw Error('detail-owner');
        }
      }
      const duration = Math.round((performance.now()-start)*1e6);
      if (!Number.isSafeInteger(duration) || duration < 0) throw Error('timing');
      statuses[String(r.status)] = (statuses[String(r.status)] || 0)+1;
      return duration;
    } finally { clearTimeout(timer); }
  }
  for (let i=0;i<rounds;i++) {
    const tasks=Array.from({length:width},(_,j)=> (i+j)%2 === 0 ? read(list+'?limit=2','list') : read(detail,'detail'));
    // allSettled ensures an outstanding request cannot outlive the evidence step.
    const results = await Promise.allSettled(tasks);
    if (results.some(x=>x.status!=='fulfilled')) throw Error('read-batch-failed');
    samples.push(...results.map(x=>x.value));
  }
  // Repeated default-cache reads, bidirectional foreign checks and own detail
  // from B; separate from timed samples, all using actual browser session.
  if (extraChecks) {
    if (role === 'a') {
      const saved=cursor;
      if (!saved) throw Error('cursor');
      for (let j=0;j<2;j++) await read(list+'?limit=2&cursor='+encodeURIComponent(saved),'next');
      await read(detailB,'detail-b');
      await read(list+'?limit=2','list');
    } else {
      await read(detailB,'detail-b');
      await read(detailB,'detail-b');
      await read(detail,'detail');
      await read(list+'?limit=2','list');
    }
  }
  if (checkCursor !== null) {
    for (const path of [list+'?limit=2&cursor='+encodeURIComponent(checkCursor),list+'?limit=2&cursor=invalid-lab-cursor',list+'?limit=2&limit=2']) await read(path,'negative');
  }
  return {samples, statuses, cursor};
}'''


def _receipt(result, count, role, negatives=0, *, expected_200=None, expected_404=None, extra=0):
    if set(result) != {'samples', 'statuses', 'cursor'}:
        raise AssertionError('unexpected receipt shape')
    if len(result['samples']) != count:
        raise AssertionError('missing load samples')
    status = result['statuses']
    if not isinstance(status, dict) or any(type(v) is not int or v < 0 for v in status.values()):
        raise AssertionError('invalid status counters')
    if sum(status.values()) != count + negatives + extra:
        raise AssertionError('status total mismatch')
    if any(k not in ('200','400','403','404','422') for k in status):
        raise AssertionError('unexpected status')
    if expected_200 is not None:
        if status.get('200',0) != expected_200:
            raise AssertionError('wrong success count')
        # Some cursor negatives may also return 404; all ordinary foreign
        # checks must return 404, not any other allowed negative code.
        if not expected_404 <= status.get('404',0) <= expected_404+negatives:
            raise AssertionError('wrong foreign count')
    elif role == 'a' and status != {'200': count}:
        raise AssertionError('unexpected A status')
    elif role == 'b' and (not status.get('200') or not status.get('404')):
        raise AssertionError('unexpected B status')
    return {'latency': percentiles(result['samples']), 'http_status_counts': status}


def measure_bounded_load(pa, pb, owner_a, owner_b, stage):
    if stage not in ('source','restore') or not isinstance(owner_a,str) or not isinstance(owner_b,str) or not owner_a or not owner_b or owner_a == owner_b:
        raise ValueError('invalid scope')
    # Ordinary browser pages must already be at the exact lab origin. The lab
    # DNS/network is isolated by the orchestrator; this helper cannot run alone.
    for page in (pa,pb):
        if page.url != 'https://ragfinance.ir/':
            raise ValueError('unexpected lab page')
    return _measure(pa,pb,owner_a,owner_b,stage)


def _measure(pa,pb,owner_a,owner_b,stage):
    # Internal function also exercised by a local HTTP fixture; not real Auth proof.
    rows=[]
    for width in TIERS:
        last=width==TIERS[-1]
        extra=4 if last else 0
        lists=sum((i+j)%2==0 for i in range(ROUNDS) for j in range(width))
        a = pa.evaluate(JS, dict(role='a',owner=owner_a,width=width,rounds=ROUNDS,checkCursor=None,extraChecks=last))
        cursor=a['cursor']
        if not isinstance(cursor,str) or not 1 <= len(cursor) <= 512:
            raise AssertionError('missing or oversize cursor')
        b = pb.evaluate(JS, dict(role='b',owner=owner_b,width=width,rounds=ROUNDS,checkCursor=cursor if last else None,extraChecks=last))
        if b['cursor'] is not None:
            raise AssertionError('unexpected foreign cursor')
        rows.append({'concurrent_requests_per_actor':width,
            'a':_receipt(a,width*ROUNDS,'a',expected_200=width*ROUNDS+(3 if last else 0),expected_404=int(last),extra=extra),
            'b':_receipt(b,width*ROUNDS,'b',3 if last else 0,expected_200=lists+(3 if last else 0),expected_404=width*ROUNDS-lists+int(last),extra=extra)})
    result={'stage':stage,'scope':'bounded read-only CI synthetic workload; actors alternated, not simultaneous across contexts; not stress/soak or approved SLO',
            'requests':sum(TIERS)*ROUNDS*2+3+8,'negative_cursor_queries':3,'default_cache_replay_and_detail_checks':8,'tiers':rows,
            'target_acceptance':'NOT_ACCEPTED'}
    print('F3_LAB_BOUNDED_READ_LOAD',json.dumps(result,sort_keys=True),flush=True)
    return result
