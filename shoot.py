"""Headless screenshots of every screen (uses system Chrome via Playwright)."""
import asyncio, sys
from playwright.async_api import async_playwright
B = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
SHOTS = [("01_investigate_ronin_R2.png", "/?a=0x098B716B8Aaf21512996dC57EB0615e2383E2f96&rule=1", 9000),
         ("02_investigate_bybit.png", "/?a=0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2&rule=1", 9000),
         ("03_investigate_peel_chain_synthetic.png", "/?s=peel_chain&rule=1", 6000),
         ("04_investigate_binance_lookalike.png", "/?a=0x28C6c06298d514Db089934071355E5743bf21d60", 8000),
         ("05_batch_triage.png", "/?tab=batch&batch=1", 15000),
         ("06_pattern_lab.png", "/?tab=lab", 12000),
         ("07_watchlist_alert.png", "/?tab=watch", 5000)]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1680, "height": 1000})
        for name, path, wait in SHOTS:
            await pg.goto(B + path); await pg.wait_for_timeout(wait)
            await pg.screenshot(path="screenshots/" + name); print("saved", name)
        # scroll the side panel to show counterfactual + request
        await pg.goto(B + "/?s=scatter_gather&rule=1"); await pg.wait_for_timeout(5000)
        await pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true); document.querySelector('#panel').scrollTop=700")
        await pg.screenshot(path="screenshots/08_explainability_panel.png"); print("saved 08")
        await b.close()
asyncio.run(main())
