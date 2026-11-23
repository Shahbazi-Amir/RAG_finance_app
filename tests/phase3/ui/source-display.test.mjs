import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {sourceCredits,confidenceLabel} from '../../../apps/web/src/ui/source-metadata.ts';
import {publicHttpsUrl} from '../../../apps/web/src/ui/public-https.ts';
import {verifiedSourceUrl,verifiedSourceLocatorLabel,verifiedSourceTypeLabel} from '../../../apps/web/src/ui/source-locator.ts';

const registry=JSON.parse(readFileSync(new URL(
  '../../../packages/contracts/fixtures/product.v1.cases.json',import.meta.url),'utf8')).cases;
function fixture(name){
  const hit=registry.find(x=>x.case_id===name&&x.expected_valid);
  assert.ok(hit,'fixture not found '+name);
  return structuredClone(hit.document);
}
const source=()=>({
  resolution_status:'verified',attribution_status:'verified',
  source_type:'book',source_id:'src_book_01',
  display_title_origin:'source_record',
  credited_author_name:'نویسندهٔ آزمون',
  editorial_supervisor_name:'سردبیر متفاوت',
  speaker_name:'گویندهٔ سوم',
  locator:{kind:'url',url:'https://example.org/book',page:null,timestamp_ms:null}
});

test('source author/editor/speaker are always distinct and never inferred',()=>{
  const rows=sourceCredits(source());
  assert.deepEqual(rows.map(r=>r.role),['author','editor','speaker']);
  assert.deepEqual(rows.map(r=>r.name),[
    'نویسندهٔ آزمون','سردبیر متفاوت','گویندهٔ سوم']);
  assert.deepEqual(sourceCredits({...source(),credited_author_name:null}).map(x=>x.role),
    ['editor','speaker']);
  assert.deepEqual(sourceCredits({...source(),editorial_supervisor_name:null}).map(x=>x.role),
    ['author','speaker']);
  assert.deepEqual(sourceCredits({...source(),speaker_name:null}).map(x=>x.role),
    ['author','editor']);
  assert.equal(sourceCredits({...source(),attribution_status:'unknown'}).length,0);
  assert.equal(sourceCredits({...source(),resolution_status:'unresolved'}).length,0);
  assert.equal(sourceCredits({...source(),display_title_origin:'SYNTHETIC'}).length,0);
});

test('unknown confidence never becomes a numeric score or estimated percentage',()=>{
  const answer=fixture('valid_answer_unresolved_source');
  assert.match(confidenceLabel({...answer,confidence:null}),/گزارش نشده/);
  const desc=confidenceLabel({...answer,confidence:{
    value:0.42,meaning:'آزمایشی و کم‌اطمینان',
    calibration_scope:'مجموعهٔ آزمون تعریف‌شده'
  }});
  assert.match(desc,/کم‌اطمینان/);
  assert.match(desc,/مجموعهٔ آزمون/);
  assert.doesNotMatch(desc,/42%|۴۲٪|0\.42/);
  assert.match(confidenceLabel({...answer,confidence:{
    value:99,meaning:'نامعتبر',calibration_scope:'آزمون'
  }}),/قابل گزارش نیست/);
});

test('verified source links require an actually public safe HTTPS URL',()=>{
  assert.equal(verifiedSourceUrl(source()),'https://example.org/book');
  for(const url of [
    'http://example.org','javascript:alert(1)','https://127.0.0.1/',
    'https://localhost/','https://service.internal/',
    'https://site.local/','https://foo','https://[::1]/',
    'https://user:pass@example.org/', 'https://example.org:8443/',
    'https://example.org/#x','https://example.org\\@evil.test/',
    ' https://example.org/','https://example.org/path '
  ]){
    assert.equal(publicHttpsUrl(url),null,url);
    assert.equal(verifiedSourceUrl({...source(),locator:{
      kind:'url',url,page:null,timestamp_ms:null
    }}),null,url);
  }
  assert.equal(verifiedSourceUrl({...source(),attribution_status:'unknown'}),null);
  assert.equal(verifiedSourceUrl({...source(),resolution_status:'unresolved'}),null);
});


test('five verified source locators render correct type and faithful text without invented deep links',()=>{
  const website={...source(),source_type:'website',source_id:'site_01',
    locator:{kind:'url',url:'https://example.org/verified',page:null,timestamp_ms:null}};
  const bookPage={...source(),source_type:'book',
    locator:{kind:'book_page',url:null,page:18,timestamp_ms:null}};
  const bookAnchor={...source(),source_type:'book',
    locator:{kind:'book_anchor',url:null,page:null,timestamp_ms:null,
      work_id:'work1',edition_id:'edition2',anchor:'section3'}};
  const transcriptTime={...source(),source_type:'transcript',
    locator:{kind:'transcript_timestamp',url:null,page:null,timestamp_ms:180000}};
  const transcriptSegment={...source(),source_type:'transcript',
    locator:{kind:'transcript_segment',url:null,page:null,timestamp_ms:null,
      episode_id:'episode_01',segment_anchor:'section_02'}};
  const cases=[
    [website,'وب‌سایت',/نشانی وب/],
    [bookPage,'کتاب',/صفحه.*18/],
    [bookAnchor,'کتاب',/work1.*edition2.*section3/],
    [transcriptTime,'متن گفتار',/180000/],
    [transcriptSegment,'متن گفتار',/episode_01.*section_02/]
  ];
  for(const [candidate,type,text] of cases){
    assert.equal(verifiedSourceTypeLabel(candidate),type);
    assert.match(verifiedSourceLocatorLabel(candidate),text);
    assert.equal(verifiedSourceUrl(candidate),candidate===website?
      'https://example.org/verified':null);
  }
  for(const candidate of [bookPage,bookAnchor,transcriptTime,transcriptSegment]){
    assert.match(verifiedSourceLocatorLabel(candidate),/صفحه|نشانگر|زمان|بخش/);
    assert.equal(verifiedSourceUrl(candidate),null);
  }
});

test('unverified/unsafe/mistyped locators fail closed, including forged author and wrong resource kind',()=>{
  const url={...source(),source_type:'website',
    locator:{kind:'url',url:'https://example.org/verified',page:null,timestamp_ms:null}};
  const cases=[
    {...url,attribution_status:'unknown'},
    {...url,resolution_status:'unresolved'},
    {...url,display_title_origin:'SYNTHETIC'},
    {...url,source_id:null},
    {...url,source_type:'book'},
    {...url,locator:{...url.locator,url:'javascript:alert(1)'}},
    {...url,locator:{kind:'book_anchor',url:null,page:null,timestamp_ms:null,
      work_id:'work',edition_id:'edition',anchor:'part'}},
    {...url,source_type:'book',
      locator:{kind:'book_page',url:null,page:0,timestamp_ms:null}},
    {...url,source_type:'transcript',
      locator:{kind:'transcript_timestamp',url:null,page:null,timestamp_ms:-1}},
    {...url,source_type:'transcript',
      locator:{kind:'transcript_segment',url:null,page:null,timestamp_ms:null,
        episode_id:'episode',segment_anchor:' '}}
  ];
  for(const candidate of cases){
    assert.equal(verifiedSourceLocatorLabel(candidate),null);
    assert.equal(verifiedSourceTypeLabel(candidate),null);
  }
  assert.equal(verifiedSourceLocatorLabel({...url,locator:null}),null);
});
