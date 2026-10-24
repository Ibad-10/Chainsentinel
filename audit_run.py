"""Live audit driver: hits the same HTTP API the UI uses and saves what came back (docs/audit/runs.json).
Run against a server started with CS_AUDIT=1 and without CS_OFFLINE. Usage: .venv/bin/python audit_run.py [base_url]"""
import sys, json, time, requests, os, random
B = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
RPC = "https://ethereum-rpc.publicnode.com"
out = {"started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "runs": []}
def rpc(m, p): return requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": m, "params": p}, timeout=20).json()["result"]
def inv(label, addr, refresh=True):
    # refresh=True is the UI's "Re-fetch live data" box: chain data straight from the network, never the disk cache
    t0 = time.time(); r = requests.get(f"{B}/api/analyze", params={"address": addr, "refresh": str(refresh).lower()}, timeout=600); ms = int((time.time() - t0) * 1000)
    if r.status_code != 200: out["runs"].append(dict(feature="investigate", label=label, address=addr, error=r.text[:300], ms=ms)); print(label, "ERROR", r.text[:200]); return None
    d = r.json(); pv = d["provenance"]
    row = dict(feature="investigate", label=label, address=addr, ms=ms, verdict=d["verdict"], verdict_facts=d["verdict_facts"], rules=[x["id"] for x in d["rules"]], n_tx=d["n_tx"],
               p_violation=round(d["sapling_full"]["probabilities"]["violation"], 3), status=d["sapling_full"]["status"], **pv)
    out["runs"].append(row); print(label, json.dumps(row)[:400]); return d
# 1. showcase wallets
inv("Bybit Exploiter", "0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2")
inv("Ronin Bridge Exploiter", "0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
inv("Coinbase 10", "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43")
# 2a. a random active address from the newest block (never cached)
head = int(rpc("eth_blockNumber", []), 16); blk = rpc("eth_getBlockByNumber", [hex(head), True])
cands = [t["from"] for t in blk["transactions"] if int(t["value"], 16) > 0]
random.seed(head); pick = random.choice(cands)
out["fresh_pick"] = dict(block=head, address=pick)
inv(f"Random sender in block #{head}", pick, refresh=False)
# 2b. a recently added OFAC-listed ETH address (last lines of the 0xB10C list)
ofac = [l.strip() for l in open("data/ofac_eth.txt") if l.strip()]
# 2b. an OFAC-listed ETH address never investigated before (no cache file): walk the 0xB10C list from the newest end
import hashlib
def cached_before(a): return os.path.exists(os.path.join("cache", hashlib.sha1(json.dumps(["eth", a.lower(), 1000, 4, "v3"], sort_keys=True).encode()).hexdigest() + ".json"))
ofac_pick = next(a for a in reversed(ofac) if not cached_before(a))
out["ofac_pick"] = ofac_pick
inv("OFAC-listed ETH address (not cached)", ofac_pick, refresh=False)
# 3. policy editor: drop R2 (mixers) from the policy and re-run Sapling on the Bybit evidence
pol = requests.get(f"{B}/api/sapling/policy").json()
d = requests.get(f"{B}/api/analyze", params={"address": "0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2"}).json()
edited = "\n".join(l for l in pol["policy"].splitlines() if not l.startswith("R2 ")) + "\nR9 Large transfers: any single transfer above 1,000 ETH needs a documented business reason."
t0 = time.time(); r = requests.post(f"{B}/api/sapling/verify", json=dict(policy=edited, evidence=d["sapling_full"]["request"]["evidence"], claim=pol["claim"]), timeout=300).json()
row = dict(feature="policy-editor", label="Bybit evidence, policy without R2 + new R9", ms=int((time.time() - t0) * 1000), verdict=r.get("verdict"), src=r.get("src"),
           p_violation=round(r["probabilities"]["violation"], 3), status=r.get("status"), model_ms=(r.get("timing_ms") or {}).get("model"), attempts=r.get("attempts"), sha=r.get("request_sha256"),
           default_verdict=d["verdict"], default_p_violation=round(d["sapling_full"]["probabilities"]["violation"], 3))
out["runs"].append(row); print(row)
# 4. batch triage, forced live
t0 = time.time(); b = requests.get(f"{B}/api/batch", params={"refresh": 1}, timeout=1200).json()
rows = [dict(title=i["title"], kind=i["kind"], verdict=i["verdict"], expected=i["expected"], rules=i.get("rules"), chain_src=(i.get("prov") or {}).get("chain_src"),
             sapling_src=(i.get("prov") or {}).get("sapling_src"), sapling_ms=(i.get("prov") or {}).get("sapling_ms"), newest_tx_block=(i.get("prov") or {}).get("newest_tx_block"),
             newest_tx_ts=(i.get("prov") or {}).get("newest_tx_ts"), error=i.get("error")) for i in b["items"]]
out["runs"].append(dict(feature="batch", ms=int((time.time() - t0) * 1000), run_ms=b.get("run_ms"), reused=b.get("reused"), items=rows)); print("batch", b.get("run_ms"), [(x["title"][:20], x["verdict"], x["chain_src"], x["sapling_src"]) for x in rows])
out["finished"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
json.dump(out, open("docs/audit/runs.json", "w"), indent=1)
