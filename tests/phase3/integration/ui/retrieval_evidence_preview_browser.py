#!/usr/bin/env python3
"""Isolated Next+Chromium source-state DOM check, explicitly synthetic only."""
import os
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect


def main():
    base=os.getenv("UI_CHAT_L1_BASE_URL","http://127.0.0.1:3000")
    url=urlsplit(base)
    if url.scheme!="http" or url.hostname!="127.0.0.1" or url.port!=3000:
        raise RuntimeError("CI_EVIDENCE_PREVIEW_LOOPBACK_ONLY")
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            for size in ((1280,800),(390,844)):
                page=browser.new_page(viewport={"width":size[0],"height":size[1]})
                try:
                    page.goto(base+"/ci-evidence-preview",wait_until="domcontentloaded")
                    expect(page.get_by_test_id("synthetic-only")).to_contain_text(
                        "هیچ منبع C018 واقعی")
                    section=page.get_by_test_id("retrieval-evidence-list")
                    expect(section.get_by_role("heading",name="شواهد بازیابی")).to_be_visible()
                    assert section.locator("li").count()==5
                    assert section.locator("a").count()==1
                    assert section.locator("a").first.get_attribute("href")==(
                        "https://example.org/evidence")
                    assert page.get_by_text("fixture_source_verified").count()==1
                    assert page.get_by_text("fixture_source_no_locator").count()==1
                    assert page.get_by_text("fixture_source_destination_unverified").count()==1
                    assert page.get_by_text("fixture_source_hidden").count()==0
                    assert page.get_by_text("fixture_chunk_hidden").count()==0
                    assert page.get_by_text("fixture_source_book").count()==1
                    assert section.get_by_text("صفحهٔ ثبت‌شده: 27").count()==1
                    assert section.get_by_text("منبع تأیید نشده؛ قابل استناد نیست.").count()==1
                    assert section.get_by_text("مقصد تأیید نشده؛ پیوند غیرفعال است.").count()==1
                    assert section.get_by_text("این منبع پیوند وب معتبر ندارد.").count()==2
                    print(f"UI_GATE3_SYNTHETIC_SOURCE_STATES_BROWSER_{size[0]}x{size[1]}_PASS",
                          flush=True)
                finally:
                    page.close()
        finally:
            browser.close()


if __name__=="__main__":
    main()
