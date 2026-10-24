"""Headless screenshots of every screen (uses system Chrome via Playwright). Usage: python shoot.py [base_url]"""
import asyncio, sys
from playwright.async_api import async_playwright
B = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
RONIN, BYBIT, BINANCE, COINBASE = ("0x098B716B8Aaf21512996dC57EB0615e2383E2f96", "0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2",
                                   "0x28C6c06298d514Db089934071355E5743bf21d60", "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43")
SHOTS = [("00_overview_dashboard.png", "/?tab=overview", 4500),
         ("01_investigate_ronin_R2.png", f"/?a={RONIN}&rule=1", 9000),
         ("02_investigate_bybit.png", f"/?a={BYBIT}", 9000),
         ("03_investigate_peel_chain_synthetic.png", "/?s=peel_chain&rule=1", 8000),
         ("04_investigate_binance_lookalike.png", f"/?a={BINANCE}", 9000),
         ("05_batch_triage.png", "/?tab=batch&batch=1", 6000),
         ("06_pattern_lab.png", "/?tab=lab", 8000),
         ("07_watchlist_alert.png", "/?tab=watch", 4000),
         ("10_how_it_works.png", "/?tab=how", 3000),
         ("13_investigate_coinbase_clear.png", f"/?a={COINBASE}", 9000)]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1680, "height": 1000})
        for name, path, wait in SHOTS:
            await pg.goto(B + path); await pg.wait_for_timeout(wait)
            await pg.screenshot(path="screenshots/" + name); print("saved", name)
        # explainability: counterfactual + exactly what Sapling saw
        await pg.goto(B + "/?s=scatter_gather&rule=1"); await pg.wait_for_timeout(8000)
        await pg.evaluate("document.querySelectorAll('#c-req details').forEach((d,i)=>d.open=i<2); document.querySelector('#c-cf').scrollIntoView({block:'start'})")
        await pg.wait_for_timeout(600); await pg.screenshot(path="screenshots/08_explainability_panel.png"); print("saved 08")
        # pipeline stepper: click step 3 (rules fire) on the Bybit investigation
        await pg.goto(B + f"/?a={BYBIT}"); await pg.wait_for_timeout(9000)
        await pg.click('#steps .step[data-k="2"]'); await pg.wait_for_timeout(1800)
        await pg.screenshot(path="screenshots/09_pipeline_stepper.png"); print("saved 09")
        # how it works: counterfactual and cut-offs
        await pg.goto(B + "/?tab=how"); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.querySelector('#howcf').scrollIntoView({block:'start'}); document.querySelector('#v-how .scroll').scrollTop -= 120")
        await pg.wait_for_timeout(1500); await pg.screenshot(path="screenshots/11_how_it_works_counterfactual.png"); print("saved 11")
        # watchlist refuses anything that looks like a seed phrase
        await pg.goto(B + "/?tab=watch"); await pg.wait_for_timeout(2000)
        await pg.fill("#waddr", "river candle orbit maple tunnel velvet harbor lemon prism walnut ember cobalt")
        await pg.click("#wadd"); await pg.wait_for_timeout(1200)
        await pg.screenshot(path="screenshots/12_watchlist_rejects_seed_phrase.png"); print("saved 12")
        # Sapling verdict panel mid-run ("Sapling is verifying...") and finished
        await pg.goto(B + f"/?a={RONIN}"); await pg.wait_for_selector("#sapstate.busy", timeout=15000); await pg.wait_for_timeout(250)
        await pg.screenshot(path="screenshots/14_sapling_verifying.png"); print("saved 14")
        await pg.wait_for_timeout(6000); await pg.locator("#c-verdict").screenshot(path="screenshots/15_sapling_verdict_panel.png"); print("saved 15")
        # policy editor: drop rule R8 from the written policy and re-run Sapling live on the Bybit evidence
        await pg.goto(B + f"/?a={BYBIT}"); await pg.wait_for_timeout(9000)
        await pg.click("#poledit"); await pg.wait_for_timeout(400)
        await pg.evaluate("""() => { const t = document.querySelector('#poltext'); t.value = t.value.replace(/R8[^\\n]*\\n/, ''); t.dispatchEvent(new Event('input')); }""")
        await pg.click("#polrun"); await pg.wait_for_selector("#polres .polcmp", timeout=60000); await pg.wait_for_timeout(1200)
        await pg.screenshot(path="screenshots/16_policy_editor_rerun.png"); print("saved 16")
        await pg.keyboard.press("Escape")
        # plain-English tooltip on jargon
        await pg.hover("#c-cf .gl"); await pg.wait_for_timeout(400)
        await pg.screenshot(path="screenshots/17_jargon_tooltip.png"); print("saved 17")
        # live block scanner: funnel + block feed, then a SIMULATED hit end to end
        await pg.goto(B + "/?tab=scan"); await pg.wait_for_selector("#scblocks .brow", timeout=60000); await pg.wait_for_timeout(9000)
        await pg.screenshot(path="screenshots/18_live_scanner.png"); print("saved 18")
        await pg.click("#scinj"); await pg.wait_for_function("document.querySelector('#sccards .sccard.sim .vpill')", timeout=60000); await pg.wait_for_timeout(1500)
        await pg.screenshot(path="screenshots/19_live_scanner_escalation.png"); print("saved 19")
        await b.close()
asyncio.run(main())
