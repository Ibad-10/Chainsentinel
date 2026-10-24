"""Live block scanner. Stage 1: cheap rules on EVERY transaction of each new Ethereum block.
Stage 2: only the suspicious ones go to Banyan Sapling (same policy and claim, same evidence build), rate-limited.

Sources (free, no key): a public JSON-RPC node for whole blocks (one call per block, at the chain head), with
Blockscout v2 as the fallback for block transactions, and Blockscout v2 for internal transactions once it has
indexed the block (it runs a few blocks behind the head, so internal transfers are checked a little later).
Offline (CS_OFFLINE=1): replays a recorded session of real blocks from cache/scanner_recording.json."""
import os, json, time, threading, collections, datetime as dt, requests
from concurrent.futures import ThreadPoolExecutor
import engine as E

RPCS = [u for u in os.environ.get("CS_RPC", "https://ethereum-rpc.publicnode.com,https://eth.llamarpc.com").split(",") if u]
BS = E.BS
REC_PATH = os.path.join(E.CACHE, "scanner_recording.json")
WINDOW = 50            # blocks kept in memory for the pass-through check (~10 minutes)
BIG = 50.0             # ETH: "large value" for the fresh-counterparty check
BRIDGE_MIN = 5.0       # ETH: bridge deposits below this are not escalated on their own
PASS_MIN = 10.0        # ETH: pass-through check only for forwards at least this big
FRESH_PER_BLOCK = 8    # cap on balance/nonce lookups per block
SAP_WORKERS = 2        # concurrency cap for Sapling
SAP_RATE = 1.5         # Sapling calls per second, at most
QUEUE_MAX = 25
IDLE_PAUSE = 300       # auto-pause when nobody has polled for 5 minutes
S1_NAME = "Large value with a fresh counterparty"
NAMES = dict(E.RULE_NAMES, S1=S1_NAME)
UTC = lambda ts: dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")

def rpc(method, params, timeout=12):
    err = None
    for u in RPCS:
        try:
            r = requests.post(u, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=timeout)
            j = r.json()
            if "result" in j and j["result"] is not None: return j["result"], u
            err = j.get("error")
        except Exception as e: err = e
    raise RuntimeError(f"rpc {method} failed: {err}")

def fetch_block(n):
    """-> dict(number, ts, txs=[[hash, from, to, value_eth, nonce]], source)"""
    try:
        b, u = rpc("eth_getBlockByNumber", [hex(n), True])
        txs = [[t["hash"], t["from"].lower(), (t.get("to") or "").lower() or None, int(t["value"], 16) / 1e18, int(t["nonce"], 16)] for t in b["transactions"]]
        return dict(number=n, ts=int(b["timestamp"], 16), txs=txs, source="public RPC (" + u.split("//")[1].split("/")[0] + ")")
    except Exception:
        pass
    items, params = [], {}
    for _ in range(12):
        d = E.http_json(f"{BS}/api/v2/blocks/{n}/transactions", params)
        items += d.get("items") or []
        params = d.get("next_page_params")
        if not params: break
    txs = [[t["hash"], t["from"]["hash"].lower(), ((t.get("to") or {}).get("hash") or "").lower() or None, int(t["value"]) / 1e18, t.get("nonce")] for t in items]
    ts = int(dt.datetime.fromisoformat(items[0]["timestamp"].replace("Z", "+00:00")).timestamp()) if items else int(time.time())
    return dict(number=n, ts=ts, txs=txs, source="Blockscout v2")

RS = "https://api.routescan.io/v2/network/mainnet/evm/1/etherscan/api"
def fetch_internal_rs(n):
    """Value-carrying internal transfers of block n from Routescan (free, no key, indexed within a block or two of the head)."""
    r = requests.get(RS, params=dict(module="account", action="txlistinternal", startblock=n, endblock=n, page=1, offset=1000, sort="asc"), timeout=20)
    if r.status_code != 200: return None
    d = r.json(); res = d.get("result")
    if not isinstance(res, list): return [] if str(d.get("message", "")).startswith("No transactions") else None
    return [[t["hash"], t["from"].lower(), t["to"].lower(), int(t["value"]) / 1e18] for t in res
            if int(t.get("value") or 0) and t.get("type") == "call" and t.get("isError", "0") == "0" and t.get("to")]
def fetch_internal_any(n):
    """Routescan first, Blockscout v2 as fallback. Returns (transfers or None, source name)."""
    for name, fn in (("Routescan", fetch_internal_rs), ("Blockscout v2", lambda n: fetch_internal(n, pages=2))):
        try:
            it = fn(n)
            if it: return it, name
        except Exception: pass
    return None, None
def fetch_internal(n, pages=3):
    """Value-carrying internal transfers of block n from Blockscout v2, or None if not indexed yet."""
    out, params = [], {}
    for _ in range(pages):
        r = requests.get(f"{BS}/api/v2/blocks/{n}/internal-transactions", params=params, timeout=30)
        if r.status_code != 200: return None
        d = r.json()
        for t in d.get("items") or []:
            v = int(t.get("value") or 0)
            if v and t.get("type") == "call" and t.get("success", True) and t.get("to"):  # delegatecalls repeat the same value
                out.append([t["transaction_hash"], t["from"]["hash"].lower(), t["to"]["hash"].lower(), v / 1e18])
        params = d.get("next_page_params")
        if not params: break
    return out

def bs_head():
    d = E.http_json(f"{BS}/api/v2/blocks", {"type": "block"})
    return int(d["items"][0]["height"])

def is_fresh(addr, n):
    """Zero history before block n: no sent transactions and a zero balance at block n-1."""
    nonce, _ = rpc("eth_getTransactionCount", [addr, hex(n - 1)])
    if int(nonce, 16): return False
    bal, _ = rpc("eth_getBalance", [addr, hex(n - 1)])
    return int(bal, 16) == 0

FLAG_CATS = {"ofac", "mixer", "exploit", "bridge"}
def lab(a):
    if not a: return None
    if a.startswith("0xsim"): return SIM_LABELS.get(a)
    return E.local_label(a)

class Window:
    """Last WINDOW blocks of value transfers, for rapid pass-through and the subject's recent activity."""
    def __init__(self): self.blocks = collections.deque()
    def add(self, n, transfers): self.blocks.append((n, transfers)); [self.blocks.popleft() for _ in range(max(0, len(self.blocks) - WINDOW))]
    def activity(self, a):
        rin = [(n, f, v) for n, ts in self.blocks for (h, f, t, v, k) in ts if t == a and v > 0]
        rout = [(n, t, v) for n, ts in self.blocks for (h, f, t, v, k) in ts if f == a and v > 0]
        return rin, rout
    def span(self): return (self.blocks[0][0], self.blocks[-1][0]) if self.blocks else (None, None)

def stage1(blk, window, fresh, internal=False, simulated=False):
    """Cheap rules over every transfer of a block. -> {subject: [hits]}, transfers. Each hit = (rule, detail, tx, other)."""
    n = blk["number"]
    B = (lambda x: f"simulated block {x}") if simulated else (lambda x: f"block #{x}")
    transfers = [(h, f, t, v, "internal" if internal else "tx") for h, f, t, v, *_ in blk["txs"] if t]
    hits = collections.defaultdict(list)
    def subj(f, t, flagged):  # the party under suspicion is the one trading with the labelled entity
        other = f if flagged == "to" else t
        lo = lab(other)
        return other if not (lo and lo["cat"] in FLAG_CATS) else f
    for h, f, t, v, k in transfers:
        for side, a in (("to", t), ("from", f)):
            l = lab(a)
            if not l or l["cat"] not in FLAG_CATS or v <= 0: continue  # zero-value calls (votes, approvals) are not transfers
            if side == "from" and v < 0.1: continue  # unsolicited inbound dust from a flagged address: the receiver cannot prevent it
            other = f if side == "to" else t
            s = subj(f, t, side)
            what = (f"sent {v:,.4f} ETH to" if side == "to" else f"received {v:,.4f} ETH from") + f" {l['name']}"
            where = f" ({'internal transfer' if k == 'internal' else 'transaction'} {h[:12]}…)"
            if l["cat"] == "ofac": hits[s].append(("R1", f"In {B(n)} it {what}, an OFAC-sanctioned address{where}", h, a))
            elif l["cat"] == "mixer":
                hits[s].append(("R2", f"In {B(n)} it {what}, a mixer contract{where}", h, a))
            elif l["cat"] == "exploit": hits[s].append(("R8", f"In {B(n)} it {what}, an address publicly labelled as a hack or exploit{where}", h, a))
            elif l["cat"] == "bridge" and side == "to" and v >= BRIDGE_MIN:
                hits[s].append(("R6", f"In {B(n)} it {what}, a cross-chain bridge{where}", h, a))
        if v >= BIG and fresh.get(t):
            hits[t].append(("S1", f"In {B(n)} it received {v:,.2f} ETH from {(lab(f) or {}).get('name') or f[:10] + '…'} and had no history before this block (no sent transactions, zero balance) (transaction {h[:12]}…)", h, f))
    # R3 rapid pass-through against the in-memory window
    if not internal:
        for h, f, t, v, k in transfers:
            if v < PASS_MIN or (lab(f) and lab(f)["cat"] != "unknown"): continue
            rin, _ = window.activity(f)
            got = sum(x[2] for x in rin)
            # pass-through means roughly what came in goes out; sending far more than arrived is just a funded wallet
            if got and 0.8 * got <= v <= 1.25 * got:
                first = min(x[0] for x in rin)
                hits[f].append(("R3", f"It received {got:,.2f} ETH in the last {n - first} blocks (from {B(first)}) and in {B(n)} forwarded {v:,.2f} ETH ({v / got:.0%} of it) to {(lab(t) or {}).get('name') or t[:10] + '…'}, about {max(1, round((n - first) * 12 / 60))} min later (transaction {h[:12]}…)", h, t))
    return hits, transfers

def fresh_candidates(blk):
    return [t for h, f, t, v, *_ in sorted(blk["txs"], key=lambda x: -x[3]) if t and v >= BIG and not lab(t)][:FRESH_PER_BLOCK]

def evidence(subject, hs, blk, window, simulated=False):
    n = blk["number"]; l = lab(subject)
    rin, rout = window.activity(subject)
    lo, hi = window.span()
    s = [("SIMULATED demo transaction, not real chain data. " if simulated else "") + f"Ethereum address {subject}" + (f", public label: {l['name']}" if l and l.get("name") else ", no public label") + "."]
    s.append(("Seen by ChainSentinel's live block scanner in a simulated block." if simulated else f"Seen by ChainSentinel's live block scanner in block #{n} ({UTC(blk['ts'])}).") +
             " Only the scanner's short window of recent blocks is known; the address's longer history was not fetched.")
    if rin or rout:
        s.append(f"In the {('simulated' if simulated else str((hi - lo + 1) if lo else 0))} recent blocks kept in memory it received {sum(x[2] for x in rin):,.2f} ETH in {len(rin)} transfers and sent {sum(x[2] for x in rout):,.2f} ETH in {len(rout)} transfers.")
    cps = []
    for _, _, _, other in hs:
        lo2 = lab(other)
        if lo2 and lo2.get("name") and lo2["name"] not in cps: cps.append(lo2["name"])
    if cps: s.append("Labelled counterparties: " + "; ".join(cps) + ".")
    rules = []; seen = set()
    for rid, det, _, _ in hs:
        if (rid, det) in seen: continue
        seen.add((rid, det)); rules.append(dict(id=rid, name=NAMES[rid], detail=det))
    look = []
    for _, _, _, other in hs:
        lo2 = lab(other)
        if lo2 and lo2["cat"] == "exchange": look.append(f"A counterparty ({lo2['name']}) is a labelled exchange wallet; exchange withdrawals and deposits are common and legitimate.")
    if any(r["id"] == "S1" for r in rules) and len(rules) == 1:
        look.append("Large transfers to brand-new addresses are also normal for new self-custody wallets and exchange withdrawals.")
    flags = E.flags_text(rules, sorted(set(look))).replace("no rule R1-R8 triggered", "no rule triggered")
    return " ".join(s), flags, rules

# ---------------- simulated injections (clearly labelled, never counted as real) ----------------
SIM_LABELS = {"0xsim0000000000000000000000000000000c0ffee": {"name": None, "cat": "unknown", "src": "simulated"}}
SIM_SUBJECT = "0xsim0000000000000000000000000000000c0ffee"
BYBIT = "0x47666fab8bd0ac7003bce3f5c3585383f09486e2"; TC100 = "0xa160cdab225685da1d56aa342ad8841c3b53f291"
def sim_block():
    """A fixed SIMULATED scenario: a wallet receives 120 ETH from the (real, labelled) Bybit exploiter and pushes
    100 ETH into Tornado Cash's 100 ETH pool three blocks later. The addresses it trades with are real labels;
    the transactions are not real."""
    return [dict(number=0, ts=0, txs=[["SIMULATED-1", BYBIT, SIM_SUBJECT, 120.0, 0]]),
            dict(number=3, ts=0, txs=[["SIMULATED-2", SIM_SUBJECT, TC100, 100.0, 0]])]

class Scanner:
    def __init__(self):
        self.lock = threading.RLock(); self.started = False; self.paused = False; self.idle = False
        self.mode = "replay" if E.OFFLINE else "live"
        self.recording = None
        self.last_poll = time.time(); self.window = Window(); self.cursor = None; self.head = None; self.source = None
        self.blocks = collections.deque(maxlen=40); self.cards = collections.deque(maxlen=60)
        self.tot = collections.Counter(); self.sim = collections.Counter()
        self.pending_internal = collections.deque(); self.bs_head = 0; self.bs_head_at = 0
        self.pool = ThreadPoolExecutor(SAP_WORKERS); self.inflight = 0; self.last_call = 0.0; self.rl = threading.Lock()
        self.recent = {}; self.seq = 0; self.err = None

    # ---- lifecycle
    def ensure(self):
        self.last_poll = time.time()
        if self.idle: self.idle = False
        if not self.started:
            self.started = True; threading.Thread(target=self.loop, daemon=True).start()
            if self.mode == "live": threading.Thread(target=self.internal_loop, daemon=True).start()
    def internal_loop(self):
        E.audit.CTX.feature = "scanner-internal"
        """Blockscout indexes internal transfers a little behind the head and is slow, so this runs on its own thread."""
        while True:
            try:
                if self.paused or self.idle or not self.pending_internal: time.sleep(2); continue
                before = len(self.pending_internal); self.drain_internal()
                if len(self.pending_internal) == before: time.sleep(10)
            except Exception: time.sleep(5)
    def loop(self):
        E.audit.CTX.feature = "scanner"
        while True:
            try:
                if self.paused or self.idle: time.sleep(1); continue
                if time.time() - self.last_poll > IDLE_PAUSE: self.idle = True; continue
                self.step_replay() if self.mode == "replay" else self.step_live()
            except Exception as e:
                self.err = str(e)[:200]; time.sleep(4)
    def step_live(self):
        head = int(rpc("eth_blockNumber", [])[0], 16); self.head = head
        if self.cursor is not None and head - self.cursor > 6:
            with self.lock: self.tot["skipped_blocks"] += head - self.cursor
        if self.cursor is None or head - self.cursor > 6: self.cursor = head  # start at (or jump forward to) the head
        if self.cursor > head: time.sleep(2); return
        blk = fetch_block(self.cursor)
        fresh = {}
        for a in fresh_candidates(blk):
            try: fresh[a] = is_fresh(a, blk["number"])
            except Exception: fresh[a] = False
        blk["fresh"] = fresh
        self.process(blk); self.cursor += 1
        self.pending_internal.append((blk["number"], time.time()))
        while len(self.pending_internal) > 120: self.pending_internal.popleft()
    def drain_internal(self):
        if not self.pending_internal: return
        n, seen = self.pending_internal[0]
        if time.time() - seen < 20: return  # give the indexers a block or two
        it, via = fetch_internal_any(n)
        # Nothing yet: indexers may still be catching up (Blockscout runs ~20-30 blocks behind). Retry the oldest block for up to 10 minutes.
        if not it and time.time() - seen < 600: return
        self.pending_internal.popleft()
        if not it:
            with self.lock: self.tot["internal_unavailable"] += 1
            return
        self.internal_src = via
        b = next((x for x in self.blocks if x["number"] == n), None)
        blk = dict(number=n, ts=b["ts"] if b else int(time.time()), txs=it)
        with self.lock:
            hits, _ = stage1(blk, self.window, {}, internal=True)
            self.tot["internal"] += len(it)
            if b: b["internal"] = len(it); b["internal_suspicious"] = len(hits); b["internal_src"] = via
            self.escalate(hits, blk, b)
    def step_replay(self):
        if self.recording is None:
            if not os.path.exists(REC_PATH): self.err = "No recorded session in cache/scanner_recording.json"; time.sleep(5); return
            self.recording = json.load(open(REC_PATH)); self.ri = 0
        rec = self.recording["blocks"]
        if self.ri >= len(rec):
            time.sleep(6); self.ri = 0; self.window = Window(); self.recent = {}
            with self.lock: self.tot["loops"] += 1
        blk = rec[self.ri]; self.ri += 1; self.head = rec[-1]["number"]; self.source = "replayed recording"
        self.process(blk, src="replayed recording")
        if blk.get("internal"):
            iblk = dict(number=blk["number"], ts=blk["ts"], txs=blk["internal"])
            with self.lock:
                hits, _ = stage1(iblk, self.window, {}, internal=True)
                b = self.blocks[0]; b["internal"] = len(blk["internal"]); b["internal_suspicious"] = len(hits)
                self.tot["internal"] += len(blk["internal"])
                self.escalate(hits, iblk, b)
        time.sleep(4)

    # ---- per block
    def process(self, blk, src=None):
        with self.lock:  # the window is shared with the internal-transfer thread
            hits, transfers = stage1(blk, self.window, blk.get("fresh") or {})
            self.window.add(blk["number"], [t for t in transfers if t[3] > 0])
            b = dict(number=blk["number"], ts=blk["ts"], txs=len(blk["txs"]), suspicious=len(hits), escalated=0, verdicts=collections.Counter(), source=src or blk.get("source"), internal=None, seen=int(time.time()))
            self.source = b["source"]
            self.blocks.appendleft(b); self.tot["blocks"] += 1; self.tot["txs"] += len(blk["txs"])
            self.tot["first"] = self.tot["first"] or blk["number"]; self.tot["last"] = blk["number"]
            self.escalate(hits, blk, b)
    def escalate(self, hits, blk, b, simulated=False):
        tally = self.sim if simulated else self.tot
        for subject, hs in hits.items():
            key = (subject, tuple(sorted({h[0] for h in hs})))
            if not simulated and key in self.recent and blk["number"] - self.recent[key] < WINDOW:
                with self.lock: tally["deduped"] += 1
                continue
            self.recent[key] = blk["number"]
            facts, flags, rules = evidence(subject, hs, blk, self.window, simulated)
            with self.lock:
                self.seq += 1; tally["suspicious"] += 1
                card = dict(id=self.seq, block=blk["number"], ts=blk["ts"], subject=subject, simulated=simulated, rules=rules, txs=sorted({h[2] for h in hs}),
                            counterparties=[dict(address=h[3], label=(lab(h[3]) or {}).get("name"), real=not h[3].startswith("0xsim")) for h in hs],
                            status="queued", evidence=facts + " " + flags, src=b.get("source") if b else None)
                if self.inflight >= QUEUE_MAX: card["status"] = "skipped"; tally["skipped"] += 1; self.cards.appendleft(card); continue
                self.inflight += 1; self.cards.appendleft(card)
                if b: b["escalated"] += 1
            self.pool.submit(self.verify, card, b, tally)
    def verify(self, card, b, tally):
        E.audit.CTX.feature = "scanner-sapling"
        try:
            with self.rl:  # global rate limit across workers
                wait = self.last_call + 1 / SAP_RATE - time.time()
                if wait > 0: time.sleep(wait)
                self.last_call = time.time()
            card["status"] = "verifying"; card["t0"] = time.time()
            r = E.sapling(card["evidence"])
            v = E.decide(r["probabilities"])
            card.update(status="done", verdict=v, sapling={k: r.get(k) for k in ("status", "raw_label", "prediction_set", "probabilities", "timing_ms", "usage", "from_cache", "wall_ms", "src", "attempts", "request_sha256", "fallback_reason")})
            with self.lock:
                tally["escalated"] += 1; tally[v] += 1
                if b: b["verdicts"][v] += 1
        except Exception as e:
            msg = str(e)
            card.update(status="error", error=("Offline: no recorded Sapling answer for this exact evidence." if E.OFFLINE else "Sapling call failed: " + msg[:160]))
            with self.lock: tally["errors"] += 1
        finally:
            with self.lock: self.inflight -= 1

    # ---- API helpers
    def inject(self):
        """Run a fixed SIMULATED scenario through the same stage-1 rules and Sapling. Counted separately, badged SIMULATED."""
        sw = Window(); merged = collections.defaultdict(list); blocks = sim_block()
        for blk in blocks:
            hits, transfers = stage1(blk, sw, {}, simulated=True)
            for k, v in hits.items(): merged[k] += v
            sw.add(blk["number"], [t for t in transfers if t[3] > 0])
        b = self.blocks[0] if self.blocks else None
        with self.lock: self.sim["injected"] += 1
        ids = []
        for subject, hs in merged.items():
            facts, flags, rules = evidence(subject, hs, blocks[-1], sw, simulated=True)
            with self.lock:
                self.seq += 1; self.sim["suspicious"] += 1
                card = dict(id=self.seq, block=b["number"] if b else None, ts=int(time.time()), subject=subject, simulated=True, rules=rules, txs=sorted({h[2] for h in hs}),
                            counterparties=[dict(address=h[3], label=(lab(h[3]) or {}).get("name"), real=not h[3].startswith("0xsim")) for h in hs],
                            status="queued", evidence=facts + " " + flags, src="SIMULATED")
                self.cards.appendleft(card); self.inflight += 1
            self.pool.submit(self.verify, card, None, self.sim); ids.append(card["id"])
        return ids
    def state(self):
        with self.lock:
            bl = [dict(b, verdicts=dict(b["verdicts"])) for b in list(self.blocks)[:30]]
            cards = [{k: v for k, v in c.items() if k != "t0"} | ({"elapsed_ms": int((time.time() - c["t0"]) * 1000)} if c.get("status") == "verifying" else {}) for c in list(self.cards)[:40]]
            rec = None
            if self.mode == "replay" and self.recording: rec = dict(first=self.recording["blocks"][0]["number"], last=self.recording["blocks"][-1]["number"], recorded=self.recording.get("recorded"), n=len(self.recording["blocks"]))
            return dict(mode=self.mode, paused=self.paused, idle=self.idle, head=self.head, source=self.source, error=self.err, recording=rec, totals=dict(self.tot), simulated=dict(self.sim), blocks=bl, cards=cards,
                        limits=dict(workers=SAP_WORKERS, rate=SAP_RATE, window=WINDOW, big=BIG, bridge_min=BRIDGE_MIN, pass_min=PASS_MIN), inflight=self.inflight, pending_internal=len(self.pending_internal), internal_src=getattr(self, "internal_src", None))

SCANNER = Scanner()

def record(n_blocks=12, behind=30):
    """Capture a session of REAL recent blocks for offline replay (run online). Blocks end `behind` blocks before the head,
    so Blockscout has already indexed their internal transfers."""
    head = int(rpc("eth_blockNumber", [])[0], 16)
    out = []
    for n in range(head - behind - n_blocks + 1, head - behind + 1):
        blk = fetch_block(n); fresh = {}
        for a in fresh_candidates(blk):
            try: fresh[a] = is_fresh(a, n)
            except Exception: fresh[a] = False
        blk["fresh"] = fresh
        try: blk["internal"] = fetch_internal(n, pages=3) or []
        except Exception: blk["internal"] = []
        out.append(blk); print("recorded", n, len(blk["txs"]), "txs", len(blk["internal"]), "internal", flush=True)
    rec = dict(recorded=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), note="Replayed recording of real Ethereum mainnet blocks", blocks=out)
    json.dump(rec, open(REC_PATH, "w"), separators=(",", ":"))
    return rec
