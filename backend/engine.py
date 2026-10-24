"""ChainSentinel engine: fetch -> label -> graph -> rules detect -> Sapling decides."""
import json, os, time, hashlib, collections, statistics, datetime as dt, requests
from concurrent.futures import ThreadPoolExecutor
import sapling_client as SC, synth as SY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); CACHE = os.path.join(ROOT, "cache")
os.makedirs(CACHE, exist_ok=True)
OFFLINE = os.environ.get("CS_OFFLINE") == "1"
BS = "https://eth.blockscout.com"; MP = "https://mempool.space/api"
OFAC_ETH = {l.strip().lower() for l in open(os.path.join(DATA, "ofac_eth.txt")) if l.strip()}
OFAC_XBT = {l.strip() for l in open(os.path.join(DATA, "ofac_xbt.txt")) if l.strip()}
ESL = json.load(open(os.path.join(DATA, "etherscan_account_labels.json")))  # brianleect/etherscan-labels (MIT)
KNOWN = {
 "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash: Router", "0x722122df12d4e14e13ac3b6895a86e84145b6967": "Tornado Cash: Proxy",
 "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc": "Tornado Cash: 0.1 ETH", "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936": "Tornado Cash: 1 ETH",
 "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": "Tornado Cash: 10 ETH", "0xa160cdab225685da1d56aa342ad8841c3b53f291": "Tornado Cash: 100 ETH",
 "0x098b716b8aaf21512996dc57eb0615e2383e2f96": "Ronin Bridge Exploiter", "0x0d043128146654c7683fbf30ac98d7b2285ded00": "Harmony Bridge Exploiter",
 "0x47666fab8bd0ac7003bce3f5c3585383f09486e2": "Bybit Exploiter", "0xd37bbe5744d730a1d98d8dc97c42f0ca46ad7146": "THORChain Router",
 "0x8eb8a3b98659cce290402893d0123abb75e3ab28": "Avalanche Bridge", "0x3ee18b2214aff97000d974cf647e7c347e8fa585": "Wormhole Bridge",
}
CATS = [("ofac", ["sanction", "ofac"]), ("exploit", ["exploit", "hack", "heist", "phish", "drainer", "scam", "lazarus"]),
        ("mixer", ["tornado", "mixer", "sinbad", "blender"]), ("bridge", ["bridge", "thorchain", "wormhole", "multichain", "stargate", "across", "hop protocol"]),
        ("exchange", ["binance", "coinbase", "kraken", "bitfinex", "gemini", "upbit", "crypto-com", "crypto.com", "huobi", "okx", "kucoin", "ftx", "gate", "bybit", "exchange", "fiat-gateway", "hot wallet", "custody", "deposit"]),
        ("dex", ["uniswap", "dex", "1inch", "router", "sushiswap", "curve", "0x-protocol"])]
def categorise(text):
    t = (text or "").lower()
    for c, kws in CATS:
        if any(k in t for k in kws): return c
    return "unknown"

# ---------------- disk cache ----------------
def _ck(*parts): return os.path.join(CACHE, hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest() + ".json")
def cached(key, fn, refresh=False):
    p = _ck(*key)
    if os.path.exists(p) and (not refresh or OFFLINE):
        return json.load(open(p))
    if OFFLINE: raise RuntimeError("offline and not cached: %s" % (key,))
    try:
        v = fn()
    except Exception:
        if os.path.exists(p): return json.load(open(p))
        raise
    json.dump(v, open(p, "w")); return v
def http_json(url, params=None):
    for i in range(3):
        try:
            r = requests.get(url, params=params, timeout=40)
            if r.status_code == 200: return r.json()
        except Exception: pass
        time.sleep(1.5 * (i + 1))
    raise RuntimeError("fetch failed " + url)

# ---------------- labels ----------------
_LC_PATH = os.path.join(DATA, "label_cache.json")
LABEL_CACHE = json.load(open(_LC_PATH)) if os.path.exists(_LC_PATH) else {}
def save_labels(): json.dump(LABEL_CACHE, open(_LC_PATH, "w"))
def local_label(a, chain="eth", extra=None):
    if extra and a in extra: n, c = extra[a]; return {"name": n, "cat": c, "src": "synthetic"}
    if chain == "btc":
        return {"name": "OFAC SDN address", "cat": "ofac", "src": "OFAC list"} if a in OFAC_XBT else None
    a = a.lower()
    name = KNOWN.get(a); src = "curated"
    if not name and a in ESL: name = ESL[a]["name"] + " [" + ",".join(ESL[a]["labels"]) + "]"; src = "etherscan-labels"
    if a in OFAC_ETH: return {"name": (name or "Sanctioned address") + " [OFAC]", "cat": "ofac", "src": "OFAC list"}
    if name: return {"name": name, "cat": categorise(name), "src": src}
    if a in LABEL_CACHE: return LABEL_CACHE[a]
    return None
def blockscout_label(a):
    a = a.lower()
    if a in LABEL_CACHE: return LABEL_CACHE[a]
    if OFFLINE: return None
    try:
        d = http_json(f"{BS}/api/v2/addresses/{a}")
        tags = (d.get("metadata") or {}).get("tags") or []
        names = [t["name"] for t in tags if t.get("tagType") == "name"] + ([d["name"]] if d.get("name") else [])
        gen = [t["name"] for t in tags if t.get("tagType") == "generic"]
        info = " ".join(" ".join(t.get("meta", {}).get("info", []) or []) for t in tags)
        if not names and not gen:
            v = {"name": None, "cat": "unknown", "src": "blockscout", "contract": d.get("is_contract")}
        else:
            nm = (names[0] if names else gen[0]) + (" [" + ",".join(gen) + "]" if gen else "")
            cat = "ofac" if ("SANCTIONED" in gen or "OFAC" in info) else categorise(nm + " " + info)
            v = {"name": nm, "cat": cat, "src": "blockscout tags", "contract": d.get("is_contract")}
    except Exception:
        return None
    LABEL_CACHE[a] = v; return v
def label(a, chain="eth", extra=None, remote=False):
    l = local_label(a, chain, extra)
    if l: return l
    if remote and chain == "eth": l = blockscout_label(a)
    return l or {"name": None, "cat": "unknown", "src": None}

# ---------------- fetchers -> normalised txs ----------------
def _bs(action, a, offset, sort="asc"):
    return http_json(f"{BS}/api", dict(module="account", action=action, address=a, sort=sort, page=1, offset=offset)).get("result") or []
def fetch_eth(addr, refresh=False, max_tx=1000, hop2=4):
    a = addr.lower()
    def go():
        out = []
        for t in _bs("txlist", a, max_tx):
            if t.get("isError") != "0": continue
            out.append(dict(hash=t["hash"], frm=t["from"], to=t["to"] or t.get("contractAddress"), value=int(t["value"]) / 1e18, asset="ETH", ts=int(t["timeStamp"]), kind="native", hop=1))
        for t in _bs("txlistinternal", a, max_tx):
            if t.get("isError", "0") != "0": continue
            out.append(dict(hash=t.get("hash") or t.get("transactionHash"), frm=t["from"], to=t["to"] or t.get("contractAddress"), value=int(t["value"]) / 1e18, asset="ETH", ts=int(t["timeStamp"]), kind="internal", hop=1))
        for t in _bs("tokentx", a, 500):
            dec = int(t.get("tokenDecimal") or 18)
            out.append(dict(hash=t["hash"], frm=t["from"], to=t["to"], value=int(t["value"]) / 10 ** dec, asset=t.get("tokenSymbol") or "TOKEN", ts=int(t["timeStamp"]), kind="token", hop=1))
        # hop-2: follow the biggest native outflow recipients (bounded)
        outv = collections.defaultdict(float); first = {}
        for t in out:
            if t["frm"] == a and t["asset"] == "ETH" and t["to"]:
                outv[t["to"]] += t["value"]; first[t["to"]] = min(first.get(t["to"], 1e12), t["ts"])
        cands = [c for c, v in sorted(outv.items(), key=lambda kv: -kv[1]) if v > 1 and local_label(c) is None][:hop2]
        def h2(c):
            res = []
            for t in _bs("txlist", c, 150):
                if t.get("isError") != "0" or t["from"] != c or int(t["timeStamp"]) < first[c]: continue
                res.append(dict(hash=t["hash"], frm=c, to=t["to"], value=int(t["value"]) / 1e18, asset="ETH", ts=int(t["timeStamp"]), kind="native", hop=2))
            return res
        with ThreadPoolExecutor(4) as ex:
            for r in ex.map(h2, cands): out += r
        return out
    return cached(("eth", a, max_tx, hop2, "v2"), go, refresh)
def fetch_btc(addr, refresh=False, peel_hops=6):
    def go():
        txs = http_json(f"{MP}/address/{addr}/txs/chain")
        if len(txs) >= 25:
            try: txs += http_json(f"{MP}/address/{addr}/txs/chain/{txs[-1]['txid']}")
            except Exception: pass
        info = http_json(f"{MP}/address/{addr}")["chain_stats"]
        out = []
        def edges_of(t, focus, hop):
            ins = [v.get("prevout", {}) for v in t["vin"]]; outs = t["vout"]; ts = t["status"].get("block_time") or 0
            in_addrs = [i.get("scriptpubkey_address") for i in ins if i.get("scriptpubkey_address")]
            res = []
            if focus in in_addrs:
                for o in outs:
                    if o.get("scriptpubkey_address") and o["scriptpubkey_address"] != focus:
                        res.append(dict(hash=t["txid"], frm=focus, to=o["scriptpubkey_address"], value=o["value"] / 1e8, asset="BTC", ts=ts, kind="btc", hop=hop))
            else:
                mine = sum(o["value"] for o in outs if o.get("scriptpubkey_address") == focus) / 1e8
                src = in_addrs[0] if in_addrs else "coinbase"
                if mine: res.append(dict(hash=t["txid"], frm=src, to=focus, value=mine, asset="BTC", ts=ts, kind="btc", hop=hop))
            return res
        for t in txs: out += edges_of(t, addr, 1)
        # peel trace: follow the large 'remainder' output of 2-output spends
        spends = sorted([t for t in txs if any(v.get("prevout", {}).get("scriptpubkey_address") == addr for v in t["vin"])], key=lambda t: t["status"].get("block_time") or 0)
        cur_t = spends[0] if spends else None; cur = addr
        for h in range(peel_hops):
            if not cur_t or len(cur_t["vout"]) != 2: break
            o = sorted(cur_t["vout"], key=lambda x: x["value"])
            if o[0]["value"] > 0.25 * o[1]["value"] or not o[1].get("scriptpubkey_address"): break
            nxt = o[1]["scriptpubkey_address"]
            if h > 0: out += edges_of(cur_t, cur, 2)
            try:
                nt = http_json(f"{MP}/address/{nxt}/txs/chain")
                sp = [t for t in nt if any(v.get("prevout", {}).get("scriptpubkey_address") == nxt for v in t["vin"])]
                cur_t = sorted(sp, key=lambda t: t["status"].get("block_time") or 0)[0] if sp else None; cur = nxt
            except Exception: break
        if cur_t and cur != addr and len(cur_t["vout"]) == 2: out += edges_of(cur_t, cur, 2)
        return {"txs": out, "info": info}
    return cached(("btc", addr, peel_hops, "v2"), go, refresh)

# ---------------- graph ----------------
def build_graph(wallet, txs, chain, extra=None, cap=60):
    w = wallet if chain == "btc" else wallet.lower()
    unit = "BTC" if chain == "btc" else "ETH"
    agg = {}
    for t in txs:
        if not t["frm"] or not t["to"]: continue
        native = t["asset"] in ("ETH", "BTC")
        k = f'{t["frm"]}->{t["to"]}:{"native" if native else t["asset"]}'
        e = agg.setdefault(k, dict(id=k, source=t["frm"], target=t["to"], asset=t["asset"] if not native else unit, native=native, value=0.0, count=0, first=t["ts"], last=t["ts"], hashes=[], hop=t.get("hop", 1)))
        e["value"] += t["value"]; e["count"] += 1; e["first"] = min(e["first"], t["ts"]); e["last"] = max(e["last"], t["ts"])
        if len(e["hashes"]) < 5: e["hashes"].append(t["hash"])
        e["hop"] = min(e["hop"], t.get("hop", 1))
    # select counterparties
    score = collections.defaultdict(float)
    for e in agg.values():
        for n in (e["source"], e["target"]):
            if n == w: continue
            score[n] += e["value"] if e["native"] else 0.02 * e["count"]
    top = sorted(score, key=lambda n: (-score[n], n))
    labelled = [n for n in top if local_label(n, chain, extra)]
    keep = set(labelled[:cap // 3])
    for n in top:
        if len(keep) >= cap - 1: break
        keep.add(n)
    # remote labels for kept unknowns (bounded)
    if chain == "eth" and not extra:
        unk = [n for n in sorted(keep) if not local_label(n)][:40]
        with ThreadPoolExecutor(8) as ex: list(ex.map(blockscout_label, unk))
        save_labels()
    nodes = {}
    for n in sorted(keep | {w}, key=lambda n: (-score.get(n, 0), n)):
        lb = label(n, chain, extra)
        nodes[n] = dict(id=n, label=lb["name"], cat=("self" if n == w and lb["cat"] == "unknown" else lb["cat"]), src=lb["src"], is_self=(n == w), score=score.get(n, 0))
    edges = [e for e in agg.values() if e["source"] in nodes and e["target"] in nodes]
    return {"nodes": list(nodes.values()), "edges": edges, "unit": unit, "wallet": w, "all_edges": agg}

# ---------------- rules ----------------
RULE_NAMES = {"R1": "Sanctions exposure (OFAC)", "R2": "Mixer deposits", "R3": "Rapid pass-through", "R4": "Fan-out / splitting",
              "R5": "Peel chain", "R6": "Chain-hopping (bridge/swap)", "R7": "Round-trip / cycle", "R8": "Exploit proceeds"}
def fmt_ts(ts): return dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC") if ts else "?"
def run_rules(G, chain, extra=None):
    w = G["wallet"]; unit = G["unit"]; E = list(G["all_edges"].values())
    cat = lambda n: label(n, chain, extra)["cat"]
    self_cat = cat(w)
    nat = [e for e in E if e["native"]]
    ins = [e for e in nat if e["target"] == w]; outs = [e for e in nat if e["source"] == w]
    tin = sum(e["value"] for e in ins); tout = sum(e["value"] for e in outs)
    rules = []; lookalikes = []
    def add(rid, detail, edges=(), nodes=()):
        rules.append(dict(id=rid, name=RULE_NAMES[rid], detail=detail, edges=list(dict.fromkeys(edges)), nodes=list(dict.fromkeys(nodes))))
    # R1
    TC_DATE = 1659916800  # OFAC designated Tornado Cash on 8 Aug 2022
    def ofac_edge(e):
        other = e["target"] if e["source"] == w else e["source"]
        if other == w or cat(other) != "ofac": return False
        if "tornado" in (label(other, chain, extra)["name"] or "").lower() and e["last"] < TC_DATE: return False
        if e["target"] == w and e["value"] < 0.1 and e["native"]: return False  # unsolicited inbound dust
        if e["target"] == w and not e["native"]: return False
        return True
    ofac_e = [e for e in E if ofac_edge(e)]
    ofac_nodes = list({(e["target"] if e["source"] == w else e["source"]) for e in ofac_e})
    dust = [e for e in E if e["target"] == w and cat(e["source"]) == "ofac" and e not in ofac_e]
    if dust: lookalikes.append(f"{len(dust)} tiny or token-only inbound transfers from sanctioned addresses look like unsolicited dusting, which the wallet owner cannot prevent; ignored for R1.")
    if self_cat == "ofac" or ofac_nodes:
        ed = [e["id"] for e in ofac_e]
        add("R1", ("The wallet itself is on the OFAC SDN list. " if self_cat == "ofac" else "") + (f"{len(ofac_nodes)} counterparties are OFAC-sanctioned." if ofac_nodes else ""), ed, ofac_nodes + ([w] if self_cat == "ofac" else []))
    # R2 mixer (direct or one hop away)
    mix = [e for e in nat if cat(e["target"]) == "mixer" and e["value"] > 0]
    if mix:
        direct = [e for e in mix if e["source"] == w]; layered = [e for e in mix if e["source"] != w]
        feed = [e["id"] for e in outs if e["target"] in {m["source"] for m in layered}]
        v = sum(e["value"] for e in mix)
        if max(e["last"] for e in mix) < TC_DATE: lookalikes.append("All mixer deposits predate the OFAC designation of Tornado Cash (8 Aug 2022), so they are not sanctions breaches in themselves; the mixer use is still a laundering indicator.")
        add("R2", f"{sum(e['count'] for e in mix)} deposits totalling {v:,.2f} {unit} into mixer contracts ({len(direct)} direct, {len(layered)} via intermediate wallets one hop away), first at {fmt_ts(min(e['first'] for e in mix))}.",
            [e["id"] for e in mix] + feed, [e["target"] for e in mix])
    # look-alike: exchange wallet
    is_exchange = self_cat == "exchange"
    if is_exchange: lookalikes.append("The wallet itself is labelled as an exchange/custody wallet: high throughput and many counterparties are expected.")
    # deposit forwarding / sweeping
    by_rec = collections.Counter(); cnt = collections.Counter()
    for e in outs: by_rec[e["target"]] += e["value"]; cnt[e["target"]] += e["count"]
    sweep = False
    rep = [e for e in outs if e["count"] >= 3 and cat(e["target"]) == "unknown"]
    funders = {cat(e["source"]) for e in ins}
    payroll = self_cat != "exchange" and len(rep) >= 10 and len(rep) >= 0.7 * len(outs) and bool(funders & {"exchange"})
    if payroll:
        sweep = True
        lookalikes.append(f"{len(rep)} recipients are paid similar amounts repeatedly at regular intervals, funded from a labelled custody/exchange account: consistent with payroll.")
    if outs and tout > 0 and not payroll:
        r0, v0 = by_rec.most_common(1)[0]
        if v0 / tout >= 0.9 and (cat(r0) == "exchange" or cnt[r0] >= 10) and cat(r0) not in ("mixer", "bridge", "ofac", "exploit"):
            sweep = True
            lookalikes.append(f"{v0 / tout:.0%} of outflow goes to one destination ({(label(r0, chain, extra)['name'] or r0[:10] + '…')}) in {cnt[r0]} repeated sweeps: consistent with deposit forwarding, not layering.")
    # R3 rapid pass-through: big inflow, most of it out within 24h
    if not is_exchange and not sweep and tin >= 10:
        rawin = sorted([(e["first"], e["value"], e["id"]) for e in ins]); fast_ids = []; fast = 0
        for e in outs:
            if any(0 <= e["first"] - t0 <= 86400 for t0, _, _ in rawin): fast += e["value"]; fast_ids.append(e["id"])
        if fast >= 0.8 * tin:
            add("R3", f"{fast:,.2f} {unit} ({fast / tin:.0%} of {tin:,.2f} {unit} received) left within 24 hours of arriving.", fast_ids + [i for _, _, i in rawin][:5])
    # R4 fan-out (native value only, unknown recipients, not exchange)
    fo = [e for e in outs if e["value"] > 0.05 and cat(e["target"]) == "unknown"]
    if fo and tin:
        # keep the densest 72h window after the largest inflow
        big = max(ins, key=lambda e: e["value"])["first"] if ins else 0
        fo = [e for e in fo if 0 <= e["first"] - big <= 3 * 86400] or fo
        if (max(e["first"] for e in fo) - min(e["first"] for e in fo)) > 3 * 86400: fo = []
    if not is_exchange and not sweep and len(fo) >= 10:
        amts = [round(e["value"], 1) for e in fo]; common = collections.Counter(amts).most_common(1)[0]
        spread = (max(e["first"] for e in fo) - min(e["first"] for e in fo)) / 3600
        # scatter-gather: do recipients converge on a collector?
        col = collections.Counter(e["target"] for e in nat if e["source"] in {f["target"] for f in fo})
        gather = [c for c, k in col.items() if k >= 3 and c != w]
        gids = [e["id"] for e in nat if e["target"] in gather and e["source"] in {f["target"] for f in fo}]
        add("R4", f"Outflow split into {len(fo)} transfers to unlabelled addresses over {spread:,.1f} h; most common amount {common[0]} {unit} ×{common[1]}." +
            (f" {len(gids)} of those wallets then forward to the same collector {gather[0][:10]}… (scatter-gather)." if gather else ""), [e["id"] for e in fo] + gids, gather)
    # R5 peel chain
    out_by = collections.defaultdict(list)
    for e in nat: out_by[e["source"]].append(e)
    path = []; cur = w; seen = {w}
    for _ in range(30):
        o = sorted(out_by.get(cur, []), key=lambda e: e["value"])
        if len(o) != 2 or o[0]["value"] > 0.25 * o[1]["value"] or o[1]["target"] in seen: break
        path += [o[0]["id"], o[1]["id"]]; cur = o[1]["target"]; seen.add(cur)
    if len(path) >= 6:
        add("R5", f"{len(path) // 2} consecutive hops each peel a small payment off and pass the large remainder to a fresh address.", path, list(seen))
    # R6 chain-hop
    br = [e for e in nat if cat(e["target"]) == "bridge" and e["value"] > 0]
    swaps = [t for t in G.get("raw", []) if t["frm"] == w and cat(t["to"]) == "dex"]
    if len(swaps) >= 4 and (max(t["ts"] for t in swaps) - min(t["ts"] for t in swaps)) < 86400:
        dex_ids = list({f'{w}->{t["to"]}:native' for t in swaps})
        add("R6", f"{len(swaps)} back-to-back token swaps through a DEX router within {(max(t['ts'] for t in swaps) - min(t['ts'] for t in swaps)) / 3600:.1f} h with no business purpose (swap layering), then funds leave to a fresh wallet.", dex_ids, [t["to"] for t in swaps])
    elif br and (sum(e["value"] for e in br) >= 0.1 * max(tin, 1e-9) or any(r["id"] in ("R1", "R8") for r in rules)):
        add("R6", f"{len(br)} transfers totalling {sum(e['value'] for e in br):,.2f} {unit} into bridge/cross-chain swap contracts, first at {fmt_ts(min(e['first'] for e in br))}.", [e["id"] for e in br], [e["target"] for e in br])
    # R7 cycle back to wallet
    cyc = None
    def dfs(n, p, depth):
        nonlocal cyc
        if cyc or depth > 5: return
        for e in out_by.get(n, []):
            if e["target"] == w and depth >= 2:
                first_out = G["all_edges"][p[0]]["first"] if p else e["first"]
                if 0 <= e["last"] - first_out <= 7 * 86400 and e["value"] >= 1: cyc = p + [e["id"]]; return
                continue
            if e["target"] not in {x.split("->")[0] for x in p} and e["target"] != w: dfs(e["target"], p + [e["id"]], depth + 1)
    dfs(w, [], 0)
    if cyc: add("R7", f"Funds leave the wallet and return to it through {len(cyc) - 1} intermediate wallets.", cyc)
    # R8 exploit
    exp_src = [e for e in E if e["target"] == w and cat(e["source"]) == "exploit" and e["native"] and e["value"] >= 1]
    if self_cat == "exploit" or exp_src or (self_cat == "ofac" and any(k in (label(w, chain, extra)["name"] or "").lower() for k in ["exploit", "hack"])):
        add("R8", ("The wallet is publicly labelled '" + (label(w, chain, extra)["name"] or "") + "'. " if self_cat in ("exploit", "ofac") and label(w, chain, extra)["name"] else "") +
            (f"It received {sum(e['value'] for e in exp_src):,.2f} from exploit-labelled wallets." if exp_src else ""), [e["id"] for e in exp_src], [w] + [e["source"] for e in exp_src])
    return rules, lookalikes, dict(tin=tin, tout=tout, n_in=sum(e["count"] for e in ins), n_out=sum(e["count"] for e in outs), self_cat=self_cat)

# ---------------- evidence + Sapling ----------------
def facts_text(G, txs, chain, stats, extra=None, synthetic=False):
    w = G["wallet"]; unit = G["unit"]; lb = label(w, chain, extra)
    ts = [t["ts"] for t in txs if t["ts"]]
    tokens = sum(1 for t in txs if t.get("kind") == "token")
    cps = sorted([n for n in G["nodes"] if not n["is_self"]], key=lambda n: (-n["score"], n["id"]))
    lab = [n for n in cps if n["label"]][:8]
    big_out = sorted([e for e in G["edges"] if e["source"] == w and e["native"]], key=lambda e: -e["value"])[:5]
    big_in = sorted([e for e in G["edges"] if e["target"] == w and e["native"]], key=lambda e: -e["value"])[:3]
    nm = lambda a: label(a, chain, extra)["name"] or (a[:10] + "… (unlabelled)")
    s = [("SYNTHETIC " if synthetic else "") + f"{'Bitcoin' if chain == 'btc' else 'Ethereum'} address {w}" + (f", public label: {lb['name']}" if lb["name"] else ", no public label") + "."]
    if ts: s.append(f"{len(txs)} transfers analysed between {fmt_ts(min(ts))} and {fmt_ts(max(ts))}.")
    s.append(f"Received {stats['tin']:,.2f} {unit} in {stats['n_in']} transfers; sent {stats['tout']:,.2f} {unit} in {stats['n_out']} transfers" + (f"; {tokens} token transfers." if tokens else "."))
    if big_in: s.append("Largest sources: " + "; ".join(f"{e['value']:,.2f} {unit} from {nm(e['source'])}" for e in big_in) + ".")
    if big_out: s.append("Largest destinations: " + "; ".join(f"{e['value']:,.2f} {unit} to {nm(e['target'])} ({e['count']} tx)" for e in big_out) + ".")
    h2 = [e for e in G["edges"] if e.get("hop") == 2 and e["native"]]
    if h2: s.append("One hop further: " + "; ".join(f"{nm(e['source'])} sent {e['value']:,.2f} {unit} to {nm(e['target'])}" for e in sorted(h2, key=lambda e: -e["value"])[:5]) + ".")
    if lab: s.append("Labelled counterparties: " + "; ".join(f"{n['label']}" for n in lab) + ".")
    return " ".join(s)
def flags_text(rules, lookalikes):
    if rules: s = "Detector findings: " + "; ".join(f"{r['id']} met ({r['name']}): {r['detail']}" for r in rules) + "."
    else: s = "Detector findings: no rule R1-R8 triggered."
    if lookalikes: s += " Legitimate look-alike indicators: " + " ".join(lookalikes)
    return s
CUT = {"flag_violation": 0.60, "clear_supported": 0.45, "clear_max_violation": 0.20}
def decide(p):
    if p.get("violation", 0) >= CUT["flag_violation"]: return "FLAG"
    if p.get("supported", 0) >= CUT["clear_supported"] and p.get("violation", 0) < CUT["clear_max_violation"]: return "CLEAR"
    return "REVIEW"
def sapling(evidence):
    payload = {"policy": SC.POLICY, "evidence": evidence, "claim": SC.CLAIM}
    def go():
        r = SC.check(evidence)
        if "error" in r: raise RuntimeError(r["error"])
        return r
    t0 = time.time(); r = cached(("sapling", payload), go); r = dict(r)
    r["request"] = payload; r["wall_ms"] = int((time.time() - t0) * 1000)
    return r
def why(rules, lookalikes, verdict, p):
    if rules:
        parts = {"R1": "it is connected to OFAC-sanctioned addresses", "R2": "it moved funds into a mixer, which breaks the trail", "R3": "money passed straight through it within a day",
                 "R4": "a large inflow was split into many similar transfers to fresh wallets", "R5": "funds were peeled off hop by hop down a chain of fresh addresses",
                 "R6": "funds were sent across chains via a bridge or swap service", "R7": "funds circled back to where they started", "R8": "the money traces to a publicly labelled exploit"}
        txt = "This wallet looks like laundering because " + ", ".join(parts[r["id"]] for r in rules) + "."
    else:
        txt = "No laundering rule fired."
    if lookalikes: txt += " Mitigating context: " + " ".join(lookalikes)
    txt += f" Sapling judged the claim that the activity is legitimate as {max(p, key=p.get).replace('_', ' ')} (P(violation)={p.get('violation', 0):.2f}, P(supported)={p.get('supported', 0):.2f}), so the verdict is {verdict}."
    if verdict == "REVIEW": txt += " The evidence does not let the model commit either way, so a human analyst should look."
    return txt

def analyze(chain, address, refresh=False, extra_txs=None, synthetic_case=None):
    extra = None; synthetic = False; meta = {}
    if synthetic_case:
        title, fn, expected = SY.CASES[synthetic_case]; w, raw = fn(); synthetic = True; extra = SY.NAMED
        txs = [dict(hash=f"synthetic-{i}", frm=t["frm"].lower(), to=t["to"].lower(), value=t["value"], asset="ETH" if t["asset"] == "ETH" else t["asset"], ts=t["ts"], kind="native" if t["asset"] == "ETH" else "token", hop=1 if w in (t["frm"], t["to"]) else 2) for i, t in enumerate(raw)]
        # dex swaps are ETH-valued calls; keep as native so they count
        for t in txs:
            if t["asset"].startswith("swap"): t["kind"] = "native"; t["asset"] = "ETH"
        chain = "eth"; address = w; meta = {"title": title, "expected": expected}
    elif chain == "btc":
        d = fetch_btc(address, refresh); txs = d["txs"]; meta["info"] = d["info"]
    else:
        txs = fetch_eth(address, refresh)
    if extra_txs: txs = txs + extra_txs; extra = dict(extra or {}); extra.update({k: tuple(v) for k, v in (extra_txs[0].get("_labels") or {}).items()})
    G = build_graph(address, txs, chain, extra); G["raw"] = txs
    rules, lookalikes, stats = run_rules(G, chain, extra)
    facts = facts_text(G, txs, chain, stats, extra, synthetic)
    flags = flags_text(rules, lookalikes)
    s_facts = sapling(facts); s_full = sapling(facts + " " + flags)
    verdict = decide(s_full["probabilities"])
    G.pop("all_edges"); G.pop("raw")
    timeline = sorted([dict(ts=t["ts"], hash=t["hash"], frm=t["frm"], to=t["to"], value=t["value"], asset=t["asset"], kind=t.get("kind"), hop=t.get("hop", 1)) for t in txs if t["value"] > 0], key=lambda t: t["ts"])
    edge_ids = {e["id"] for e in G["edges"]}
    for r in rules: r["edges_in_graph"] = [x for x in r["edges"] if x in edge_ids]
    return dict(chain=chain, address=G["wallet"], synthetic=synthetic, meta=meta, label=label(G["wallet"], chain, extra), graph=G, rules=rules, lookalikes=lookalikes, stats=stats,
                sapling_facts=s_facts, sapling_full=s_full, verdict=verdict, verdict_facts=decide(s_facts["probabilities"]), cutoffs=CUT,
                why=why(rules, lookalikes, verdict, s_full["probabilities"]), timeline=timeline[-400:], n_tx=len(txs))
