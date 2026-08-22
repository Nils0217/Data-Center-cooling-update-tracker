import os
import asyncio
import re
import duckdb
from playwright.async_api import async_playwright
from engine import submit_change_request

SBR_WS = os.getenv("BRIGHTDATA_SBR_WS_ENDPOINT")

async def scrape_vendor_specs(url: str, vendor_name: str, simulated_pue: float = None):
    print(f"Connecting to Bright Data Browser for {url}...")
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(SBR_WS)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        
        content = await page.content()
        title = await page.title()
        print(f"Page retrieved: {title}")
        await browser.close()
        
        # 若有指定模擬新數據（代表供應商改版更新了規格），否則使用預設解析值
        pue_val = simulated_pue if simulated_pue else 1.08
        
        payload = {
            "name": vendor_name,
            "url": url,
            "pue": pue_val,
            "wue": 0.01,
            "load_kw": 120.0,
            "capacity_kw": 950.0,
            "price": 54000.0
        }
        
        # 送進驗證關卡與 Change Request A
        cr_id, passed, msg = submit_change_request("A", payload)
        print(f"Submitted CR-A ({cr_id}) for '{vendor_name}' (PUE: {pue_val}): {'Queued for Port' if passed else 'Rejected'}")

if __name__ == "__main__":
    import sys
    # 支援透過指令模擬網頁規格變更：python scrape_ingest.py 1.03
    new_pue = float(sys.argv[1]) if len(sys.argv) > 1 else 1.06
    asyncio.run(scrape_vendor_specs("https://www.refjet.ai/#/technology", "RefJet Cooling Unit", simulated_pue=new_pue))
