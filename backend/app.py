"""ChainSentinel API (FastAPI). Rules detect -> Banyan Sapling decides."""
import os, sys, json, time, asyncio, re, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collections
from concurrent.futures import ThreadPoolExecutor, wait
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import audit, engine as E, showcase as S, synth as SY, scanner as SCN

ROOT = E.ROOT; WL_PATH = os.path.join(E.WDATA, "watchlist.json")
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
SERVERLESS = E.SERVERLESS

# ---------------- rate limits (best effort, in memory, per instance) ----------------
# Protects the Sapling endpoint on a public demo. Per IP: CS_RL_IP calls per CS_RL_WINDOW seconds on routes that call
# Sapling. Per instance: CS_RL_GLOBAL calls per window across everyone. Weighted: a batch run counts as 5.
RL_WINDOW = int(os.environ.get("CS_RL_WINDOW", "600"))
RL_IP = int(os.environ.get("CS_RL_IP", "10" if SERVERLESS else "1000"))
RL_GLOBAL = int(os.environ.get("CS_RL_GLOBAL", "200" if SERVERLESS else "100000"))
_RL = collections.defaultdict(collections.deque); _RL_LOCK = threading.Lock()
def client_ip(request: Request):
    xf = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip") or ""
    return (xf.split(",")[0].strip() or (request.client.host if request.client else "unknown"))[:64]
def _rl_hit(ip, weight=1):
    now = time.time()
    with _RL_LOCK:
        for k in (ip, "*"):
            q = _RL[k]
            while q and q[0] < now - RL_WINDOW: q.popleft()
        if len(_RL["*"]) + weight > RL_GLOBAL:
            raise HTTPException(429, "The public demo is busy right now (too many Sapling checks across all visitors). Please try again in a few minutes.")
        if len(_RL[ip]) + weight > RL_IP:
            wait = int(_RL[ip][0] + RL_WINDOW - now) + 1 if _RL[ip] else RL_WINDOW
            raise HTTPException(429, f"Slow down a little: this public demo allows {RL_IP} Sapling checks per {RL_WINDOW // 60} minutes per visitor, to protect the shared model endpoint. Try again in about {max(1, round(wait / 60))} min.")
        for k in (ip, "*"): _RL[k].extend([now] * weight)
        if len(_RL) > 5000:  # forget idle IPs
            for k in [k for k, q in _RL.items() if k != "*" and (not q or q[-1] < now - RL_WINDOW)]: _RL.pop(k, None)
def rate_limited(request: Request): _rl_hit(client_ip(request))
def slim(r):
    p = r["sapling_full"]["probabilities"]
    return dict(chain=r["chain"], address=r["address"], synthetic=r["synthetic"], verdict=r["verdict"], verdict_facts=r["verdict_facts"], rules=[x["id"] for x in r["rules"]],
                p=p, p_facts=r["sapling_facts"]["probabilities"], label=r["label"]["name"], lookalikes=r["lookalikes"], prov=r.get("provenance"))

@app.get("/api/analyze")
def analyze(address: str, refresh: bool = False, simulate: bool = False, _=Depends(rate_limited)):
    """simulate=1 (Ethereum only): add the clearly-labelled SIMULATED Tornado Cash deposit used by the per-browser watchlist demo."""
    chain = detect_chain(address); audit.CTX.feature = "investigate"
    if simulate and chain != "eth": raise HTTPException(400, "Simulation is available for Ethereum wallets.")
    try:
        with LOCK: return E.analyze(chain, address.strip(), refresh=refresh, extra_txs=sim_txs(address.strip()) if simulate else None)
    except Exception as e: raise HTTPException(502, f"analysis failed: {e}")
@app.get("/api/synthetic/{case}")
def synthetic(case: str, _=Depends(rate_limited)):
    if case not in SY.CASES: raise HTTPException(404)
    audit.CTX.feature = "synthetic"
    with LOCK: return E.analyze("eth", None, synthetic_case=case)
class VerifyReq(BaseModel):
    policy: str
    evidence: str
    claim: str
@app.post("/api/sapling/verify")
def sapling_verify(req: VerifyReq, _=Depends(rate_limited)):
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
    return dict(real=S.REAL, synthetic=[dict(case=k, title=v[0], expected=v[2]) for k, v in SY.CASES.items()], cutoffs=E.CUT, offline=E.OFFLINE, sapling_url=E.SC.URL, serverless=SERVERLESS,
                limits=dict(per_ip=RL_IP, window_s=RL_WINDOW))
BATCH_MEMO = {}; BATCH_SEM = threading.Semaphore(8)
@app.get("/api/batch")
def batch(request: Request, refresh: bool = False):
    """Runs every showcase wallet live (chain data per CS_CHAIN_TTL, Sapling always live). The whole run is reused for
    CS_BATCH_TTL seconds (default 600) so the Overview doesn't re-run 30 Sapling calls on every visit; ran_at says when."""
    ttl = int(os.environ.get("CS_BATCH_TTL", "600"))
    if not refresh and BATCH_MEMO.get("at", 0) > time.time() - ttl: return dict(BATCH_MEMO["r"], reused=True)
    _rl_hit(client_ip(request), weight=5 if SERVERLESS else 1)
    audit.CTX.feature = "batch"; t0 = time.time()
    def real(c):
        try:
            with (BATCH_SEM if SERVERLESS else LOCK): r = E.analyze(c["chain"], c["address"], refresh=refresh)
            return dict(kind="REAL", title=c["title"], expected=c["expected"], **slim(r))
        except Exception as e: return dict(kind="REAL", title=c["title"], address=c["address"], chain=c["chain"], error=str(e), verdict="REVIEW")
    def syn(item):
        k, (title, _, exp) = item
        try:
            with (BATCH_SEM if SERVERLESS else LOCK): r = E.analyze("eth", None, synthetic_case=k)
            return dict(kind="SYNTHETIC", title=title, expected=exp, case=k, **slim(r))
        except Exception as e: return dict(kind="SYNTHETIC", title=title, expected=exp, case=k, error=str(e), verdict="REVIEW", rules=[])
    if SERVERLESS:  # 60 s function limit: run the wallets in parallel instead of one after another
        ex = ThreadPoolExecutor(8); sf = [ex.submit(syn, i) for i in SY.CASES.items()]  # synthetic first: no chain fetch, so they finish fast
        futs = [ex.submit(real, c) for c in S.REAL] + sf
        wait(futs, timeout=float(os.environ.get("CS_BATCH_BUDGET", "48"))); ex.shutdown(wait=False, cancel_futures=True)
        items = list(S.REAL) + [dict(title=t, case=k, expected=e) for k, (t, _, e) in SY.CASES.items()]
        out = [f.result() if f.done() and not f.cancelled() else dict(kind="SYNTHETIC" if "case" in it else "REAL", title=it["title"], address=it.get("address"), chain=it.get("chain", "eth"),
               case=it.get("case"), expected=it["expected"], rules=[], verdict="REVIEW", error="Still running when the 60 s serverless limit approached. Open it on its own to check it live.")
               for f, it in zip(futs, items)]
    else: out = [real(c) for c in S.REAL] + [syn(i) for i in SY.CASES.items()]
    r = dict(items=out, cutoffs=E.CUT, ran_at=int(time.time()), run_ms=int((time.time() - t0) * 1000), offline=E.OFFLINE)
    if not any("Still running" in (i.get("error") or "") for i in out): BATCH_MEMO.update(at=time.time(), r=r)  # never reuse a partial run
    return dict(r, reused=False)

# ---------------- watchlist ----------------
DEMO_WL = os.path.join(E.DATA, "watchlist.demo.json")  # committed: two public demo addresses only. watchlist.json (yours) is gitignored.
def wl_load():
    if os.path.exists(WL_PATH): return json.load(open(WL_PATH))
    return json.load(open(DEMO_WL)) if os.path.exists(DEMO_WL) else {"items": [], "alerts": []}
def wl_save(w): E.safe_dump(w, WL_PATH, indent=1)
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
    it.setdefault("injected", []).extend(sim_txs(it["address"]))
    check_item(it, wl, refresh=False); wl_save(wl); return wl
def sim_txs(address):
    a = address.lower(); ts = int(time.time())
    return [dict(hash=f"SIMULATED-{ts}-a", frm="0xhackerwallet00000000000000000000000000", to=a, value=300.0, asset="ETH", ts=ts - 600, kind="native", hop=1,
                 _labels={"0xhackerwallet00000000000000000000000000": ["Bridge Exploiter (SIMULATED)", "exploit"], "0xtornado100eth0000000000000000000000000": ["Tornado Cash 100 ETH pool (SIMULATED)", "mixer"]}),
            dict(hash=f"SIMULATED-{ts}-b", frm=a, to="0xtornado100eth0000000000000000000000000", value=100.0, asset="ETH", ts=ts - 300, kind="native", hop=1),
            dict(hash=f"SIMULATED-{ts}-c", frm=a, to="0xtornado100eth0000000000000000000000000", value=100.0, asset="ETH", ts=ts - 200, kind="native", hop=1),
            dict(hash=f"SIMULATED-{ts}-d", frm=a, to="0xtornado100eth0000000000000000000000000", value=100.0, asset="ETH", ts=ts - 100, kind="native", hop=1)]
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
def scanner_inject(_=Depends(rate_limited)):
    """DEMO MODE: push a fixed, clearly-labelled SIMULATED suspicious transaction through the same rules and Sapling."""
    SCN.SCANNER.ensure(); ids = SCN.SCANNER.inject(); return dict(ids=ids, **SCN.SCANNER.state())

async def poller():
    while True:
        await asyncio.sleep(int(os.environ.get("CS_POLL", "60")))
        try: await asyncio.to_thread(lambda: (setattr(audit.CTX, 'feature', 'watchlist-poller'), wl_check()))
        except Exception: pass
@app.on_event("startup")
async def _start():
    if not SERVERLESS: asyncio.create_task(poller())  # no background work on Vercel; the browser watchlist re-checks on demand

app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")
@app.get("/")
def index(): return FileResponse(os.path.join(ROOT, "static", "index.html"))
