/**
 * Synthetic-only renderer acceptance. Gate3 real C018 results MUST NOT be
 * represented here. Separate from the product's authenticated session path.
 * No public or staging access is allowed; no external APIs are fetched.
 */
import {headers} from 'next/headers';
import {notFound} from 'next/navigation';
import RetrievalEvidencePanel from '../../src/ui/retrieval-evidence-panel';
import type {EvidenceDisplayRow} from '../../src/ui/retrieval-evidence-view';
import '../history/history.css';

export const dynamic='force-dynamic';

const rows:EvidenceDisplayRow[]=[
 {position:1,chunkId:'fixture_chunk_verified',sourceId:'fixture_source_verified',
  sourceVerified:true,locator:{kind:'url',verified:true,url:'https://example.org/evidence'}},
 {position:2,chunkId:'fixture_chunk_no_locator',sourceId:'fixture_source_no_locator',
  sourceVerified:true,locator:null},
 {position:3,chunkId:'fixture_chunk_destination_unverified',
  sourceId:'fixture_source_destination_unverified',sourceVerified:true,
  locator:{kind:'url',verified:false,url:'https://unverified.example/link'}},
 {position:4,chunkId:'fixture_chunk_hidden',sourceId:'fixture_source_hidden',
  sourceVerified:false,locator:{kind:'url',verified:true,url:'https://example.org/secret'}},
 {position:5,chunkId:'fixture_chunk_book',sourceId:'fixture_source_book',
  sourceVerified:true,locator:{kind:'book_page',verified:true,page:27}},
];

export default async function Preview(){
  const host=(await headers()).get('host');
  if(process.env.CI!=='true'||process.env.GITHUB_ACTIONS!=='true'||
     process.env.AUTH_RUNTIME_PROFILE!==undefined||
     process.env.AUTH_CI_PRODUCT_CHAT_MODE!=='INVITED_RESULT_STUB_CI_ONLY'||
     host!=='127.0.0.1:3000')notFound();
  return <main className="history-shell product-shell" dir="rtl">
    <section className="history-main" aria-label="آزمون نمایشی منابع">
      <h1>آزمون صرفاً ساختگی نمایش منابع</h1>
      <p role="alert" data-testid="synthetic-only">
        اطلاعات این صفحه Fixture هستند، هیچ منبع C018 واقعی یا استناد تأییدشده‌ای ندارند.
      </p>
      <RetrievalEvidencePanel rows={rows}/>
    </section>
  </main>;
}
