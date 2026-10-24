"""ChainSentinel API (FastAPI). Rules detect -> Banyan Sapling decides."""
import os, sys, json, time, asyncio, re, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import audit, engine as E, showcase as S, synth as SY, scanner as SCN

ROOT = E.ROOT; WL_PATH = os.path.join(E.DATA, "watchlist.json")
app = FastAPI(title="ChainSentinel")
ETH_RE = re.compile(r"^0x[0-9a-fA-F]{40}$"); BTC_RE = re.compile(r"^(bc1[02-9ac-hj-np-z]{11,71}|[13][1-9A-HJ-NP-Za-km-z]{25,34})$")
def detect_chain(addr):
    a = addr.strip()
    if ETH_RE.match(a): return "eth"
    if BTC_RE.match(a): return "btc"
    words = a.split()
    if len(words) in (12, 15, 18, 21, 24) or re.match(r"^(0x)?[0-9a-fA-F]{64}$", a):
        raise HTTPException(400, "That looks like a seed phrase or private key. Never paste those anywhere. ChainSentinel only needs a PUBLIC address.")
    raise HTTPException(400, "Not a valid Ethereum (0x…) or Bitcoin address.")
LOCK = threading.Lock()
def slim(r):
    p = r["sapling_full"]["probabilities"]
    return dict(chain=r["chain"], address=r["address"], synthetic=r["synthetic"], verdict=r["verdict"], verdict_facts=r["verdict_facts"], rules=[x["id"] for x in r["rules"]],
                p=p, p_facts=r["sapling_facts"]["probabilities"], label=r["label"]["name"], lookalikes=r["lookalikes"], prov=r.get("provenance"))

@app.get("/api/analyze")
def analyze(address: str, refresh: bool = False):
    chain = detect_chain(address); audit.CTX.feature = "investigate"
    try:
        with LOCK: return E.analyze(chain, address.strip(), refresh=refresh)
    except Exception as e: raise HTTPException(502, f"analysis failed: {e}")
@app.get("/api/synthetic/{case}")
def synthetic(case: str):
    if case not in SY.CASES: raise HTTPException(404)
    audit.CTX.feature = "synthetic"
    with LOCK: return E.analyze("eth", None, synthetic_case=case)
class VerifyReq(BaseModel):
    policy: str
    evidence: str
    claim: str
@app.post("/api/sapling/verify")
def sapling_verify(req: VerifyReq):
    """Re-run Banyan Sapling on a user-edited policy (policy-driven verification). Same evidence and claim."""
    audit.CTX.feature = "policy-editor"
    if len(req.policy) > 20000 or len(req.evidence) > 80000 or len(req.claim) > 2000: raise HTTPException(400, "Input too long for this demo.")
    try: r = E.sapling(req.evidence, policy=req.policy, claim=req.claim)
    except ValueError as e: raise HTTPException(400, str(e))
    except Exception as e:
        if E.OFFLINE: raise HTTPException(503, "Offline mode: Sapling has not seen this exact policy before, so there is no cached answer. Restart without CS_OFFLINE=1 to verify it live.")
        raise HTTPException(502, f"Sapling call failed: {str(e)[:200]}")
    r["verdict"] = E.decide(r["probabilities"]); r["cutoffs"] = E.CUT
    return r
@app.get("/api/sapling/policy")
def sapling_policy():
    return {"policy": E.SC.POLICY, "claim": E.SC.CLAIM, "limit_tokens": E.SAPLING_TOKEN_LIMIT}
@app.get("/api/showcase")
def showcase():
    return dict(real=S.REAL, synthetic=[dict(case=k, title=v[0], expected=v[2]) for k, v in SY.CASES.items()], cutoffs=E.CUT, offline=E.OFFLINE, sapling_url=E.SC.URL)
BATCH_MEMO = {}
@app.get("/api/batch")
def batch(refresh: bool = False):
    """Runs every showcase wallet live (chain data per CS_CHAIN_TTL, Sapling always live). The whole run is reused for
    CS_BATCH_TTL seconds (default 600) so the Overview doesn't re-run 30 Sapling calls on every visit; ran_at says when."""
    ttl = int(os.environ.get("CS_BATCH_TTL", "600"))
    if not refresh and BATCH_MEMO.get("at", 0) > time.time() - ttl: return dict(BATCH_MEMO["r"], reused=True)
    audit.CTX.feature = "batch"; t0 = time.time()
    out = []
    for c in S.REAL:
        try:
            with LOCK: r = E.analyze(c["chain"], c["address"], refresh=refresh)
            out.append(dict(kind="REAL", title=c["title"], expected=c["expected"], **slim(r)))
        except Exception as e: out.append(dict(kind="REAL", title=c["title"], address=c["address"], chain=c["chain"], error=str(e), verdict="REVIEW"))
    for k, (title, _, exp) in SY.CASES.items():
        with LOCK: r = E.analyze("eth", None, synthetic_case=k)
        out.append(dict(kind="SYNTHETIC", title=title, expected=exp, case=k, **slim(r)))
    r = dict(items=out, cutoffs=E.CUT, ran_at=int(time.time()), run_ms=int((time.time() - t0) * 1000), offline=E.OFFLINE)
    BATCH_MEMO.update(at=time.time(), r=r); return dict(r, reused=False)

# ---------------- watchlist ----------------
DEMO_WL = os.path.join(E.DATA, "watchlist.demo.json")  # committed: two public demo addresses only. watchlist.json (yours) is gitignored.
def wl_load():
    if os.path.exists(WL_PATH): return json.load(open(WL_PATH))
    return json.load(open(DEMO_WL)) if os.path.exists(DEMO_WL) else {"items": [], "alerts": []}
def wl_save(w): json.dump(w, open(WL_PATH, "w"), indent=1)
class WatchIn(BaseModel): address: str
def check_item(it, wl, refresh=True):
    audit.CTX.feature = getattr(audit.CTX, "feature", None) or "watchlist"
    with LOCK: r = E.analyze(it["chain"], it["address"], refresh=refresh, extra_txs=it.get("injected") or None)
    rules = [x["id"] for x in r["rules"]]; now = int(time.time())
    if it.get("last_verdict") is not None:
        new_tx = r["n_tx"] - it.get("n_tx", 0)
        added = [x for x in rules if x not in it.get("rules", [])]
        if r["verdict"] != it["last_verdict"] or added:
            det = "; ".join(f"{x['id']} {x['name']}: {x['detail']}" for x in r["rules"] if x["id"] in added)
            wl["alerts"].insert(0, dict(ts=now, address=it["address"], chain=it["chain"], frm=it["last_verdict"], to=r["verdict"], new_rules=added, new_tx=new_tx,
                                        text=f"{new_tx} new tx. Verdict {it['last_verdict']} → {r['verdict']}." + (f" New: {det}" if det else ""), simulated=bool(it.get("injected"))))
    it.update(last_verdict=r["verdict"], rules=rules, n_tx=r["n_tx"], last_check=now, p=r["sapling_full"]["probabilities"], label=r["label"]["name"])
    return r
@app.get("/api/watchlist")
def wl_get(): return wl_load()
@app.post("/api/watchlist")
def wl_add(w: WatchIn):
    chain = detect_chain(w.address); wl = wl_load(); a = w.address.strip()
    if any(i["address"].lower() == a.lower() for i in wl["items"]): return wl
    it = dict(chain=chain, address=a, added=int(time.time()), last_verdict=None); wl["items"].append(it)
    check_item(it, wl, refresh=False); wl_save(wl); return wl
@app.delete("/api/watchlist/{address}")
def wl_del(address: str):
    wl = wl_load(); wl["items"] = [i for i in wl["items"] if i["address"].lower() != address.lower()]; wl_save(wl); return wl
@app.post("/api/watchlist/check")
def wl_check():
    wl = wl_load()
    for it in wl["items"]:
        try: check_item(it, wl, refresh=not E.OFFLINE)
        except Exception as e: it["error"] = str(e)
    wl_save(wl); return wl
@app.post("/api/watchlist/simulate/{address}")
def wl_sim(address: str):
    """DEMO MODE: inject a clearly-labelled SYNTHETIC 100 ETH Tornado Cash deposit into a watched wallet, then re-check."""
    wl = wl_load(); it = next((i for i in wl["items"] if i["address"].lower() == address.lower()), None)
    if not it: raise HTTPException(404)
    if it["chain"] != "eth": raise HTTPException(400, "Simulation is available for Ethereum wallets.")
    a = it["address"].lower(); ts = int(time.time())
    inj = it.setdefault("injected", [])
    inj += [dict(hash=f"SIMULATED-{ts}-a", frm="0xhackerwallet00000000000000000000000000", to=a, value=300.0, asset="ETH", ts=ts - 600, kind="native", hop=1,
                 _labels={"0xhackerwallet00000000000000000000000000": ["Bridge Exploiter (SIMULATED)", "exploit"], "0xtornado100eth0000000000000000000000000": ["Tornado Cash 100 ETH pool (SIMULATED)", "mixer"]}),
            dict(hash=f"SIMULATED-{ts}-b", frm=a, to="0xtornado100eth0000000000000000000000000", value=100.0, asset="ETH", ts=ts - 300, kind="native", hop=1),
            dict(hash=f"SIMULATED-{ts}-c", frm=a, to="0xtornado100eth0000000000000000000000000", value=100.0, asset="ETH", ts=ts - 200, kind="native", hop=1),
            dict(hash=f"SIMULATED-{ts}-d", frm=a, to="0xtornado100eth0000000000000000000000000", value=100.0, asset="ETH", ts=ts - 100, kind="native", hop=1)]
    check_item(it, wl, refresh=False); wl_save(wl); return wl
@app.post("/api/watchlist/reset/{address}")
def wl_reset(address: str):
    wl = wl_load()
    for it in wl["items"]:
        if it["address"].lower() == address.lower(): it.pop("injected", None); check_item(it, wl, refresh=False)
    wl_save(wl); return wl
# ---------------- live block scanner ----------------
@app.get("/api/scanner")
def scanner_state():
    SCN.SCANNER.ensure(); return SCN.SCANNER.state()
@app.post("/api/scanner/pause")
def scanner_pause(): SCN.SCANNER.paused = True; return SCN.SCANNER.state()
@app.post("/api/scanner/resume")
def scanner_resume(): SCN.SCANNER.paused = False; SCN.SCANNER.ensure(); return SCN.SCANNER.state()
@app.post("/api/scanner/inject")
def scanner_inject():
    """DEMO MODE: push a fixed, clearly-labelled SIMULATED suspicious transaction through the same rules and Sapling."""
    SCN.SCANNER.ensure(); ids = SCN.SCANNER.inject(); return dict(ids=ids, **SCN.SCANNER.state())

async def poller():
    while True:
        await asyncio.sleep(int(os.environ.get("CS_POLL", "60")))
        try: await asyncio.to_thread(lambda: (setattr(audit.CTX, 'feature', 'watchlist-poller'), wl_check()))
        except Exception: pass
@app.on_event("startup")
async def _start(): asyncio.create_task(poller())

app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")
@app.get("/")
def index(): return FileResponse(os.path.join(ROOT, "static", "index.html"))
