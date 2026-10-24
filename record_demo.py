"""Record a silent ~90 s screen capture of the live app (Playwright + system Chrome), then convert to MP4 with ffmpeg.
Usage: python record_demo.py [base_url] [out.mp4]. Needs the server running online (not CS_OFFLINE)."""
import asyncio, glob, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright
B = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
OUT = sys.argv[2] if len(sys.argv) > 2 else "demo.mp4"
BYBIT, COINBASE = "0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2", "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43"
async def investigate(pg, addr, wait):
    await pg.fill("#addr", addr); await pg.evaluate("() => { const c = document.querySelector('#refresh'); if (c) c.checked = true; }")
    await pg.keyboard.press("Enter"); await pg.wait_for_selector("#c-verdict", timeout=120000); await pg.wait_for_timeout(wait)
async def main():
    d = tempfile.mkdtemp()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 1440, "height": 900}, record_video_dir=d, record_video_size={"width": 1440, "height": 900})
        pg = await ctx.new_page()
        await pg.goto(B + "/?tab=overview"); await pg.wait_for_timeout(5000)
        await pg.goto(B + "/?tab=investigate"); await pg.wait_for_timeout(1500)
        await investigate(pg, BYBIT, 9000)                      # live fetch -> rules -> Sapling -> FLAG
        await pg.locator("#c-ent .prov").scroll_into_view_if_needed(); await pg.locator("#c-ent .prov").hover(); await pg.wait_for_timeout(3000)
        await pg.click("#poledit"); await pg.wait_for_timeout(1500)  # edit the written policy, re-run Sapling live
        await pg.evaluate("""() => { const t = document.querySelector('#poltext'); t.value = t.value.replace(/R8[^\\n]*\\n/, ''); t.dispatchEvent(new Event('input')); }""")
        await pg.wait_for_timeout(1500); await pg.click("#polrun"); await pg.wait_for_selector("#polres .polcmp", timeout=60000); await pg.wait_for_timeout(5000)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(800)
        await investigate(pg, COINBASE, 9000)                   # a busy but legitimate exchange wallet -> CLEAR
        await pg.goto(B + "/?tab=scan"); await pg.wait_for_selector("#scblocks .brow", timeout=60000); await pg.wait_for_timeout(14000)
        await pg.goto(B + "/?tab=batch&batch=1"); await pg.wait_for_timeout(9000)
        await ctx.close(); await b.close()
    src = glob.glob(os.path.join(d, "*.webm"))[0]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28", "-preset", "veryfast", OUT], check=True)
    print("saved", OUT, os.path.getsize(OUT))
asyncio.run(main())
