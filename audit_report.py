"""Summarise CS_AUDIT=1 logs (data/audit.log by default): calls per host/feature, live vs cache, Sapling latency.
Usage: python audit_report.py [log ...] > summary.json"""
import json, sys, statistics as st
from collections import Counter, defaultdict
seen, rows = set(), []
for p in sys.argv[1:] or ["data/audit.log"]:
    for line in open(p):
        try: r = json.loads(line)
        except ValueError: continue
        k = (r.get("t"), r.get("host"), r.get("path"), r.get("key"))
        if k not in seen: seen.add(k); rows.append(r)
def stats(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return dict(n=len(xs), min=round(xs[0]), median=round(st.median(xs)), max=round(xs[-1])) if xs else dict(n=0)
by_host = Counter((r["host"], r.get("src")) for r in rows)
by_feat = defaultdict(Counter)
for r in rows:
    h = "sapling" if "huggingface" in r["host"] else "cache" if r["host"] == "(disk cache)" else "chain/labels"
    by_feat[r.get("feature") or "(worker thread)"][h + ":" + str(r.get("src"))] += 1
sap = [r for r in rows if "huggingface" in r["host"]]
status = Counter(r.get("status") for r in sap)
ok = [r for r in sap if r.get("status") == 200 and r.get("timing_ms")]
hosts_ms = {h: stats([r["ms"] for r in rows if r["host"] == h]) for h in {r["host"] for r in rows if r["host"] != "(disk cache)"}}
print(json.dumps(dict(
    window=[min(r["ts"] for r in rows), max(r["ts"] for r in rows)], total=len(rows),
    by_host_src={f"{h} [{s}]": n for (h, s), n in by_host.most_common()},
    by_feature={f: dict(c) for f, c in by_feat.items()},
    sapling=dict(network_calls=len(sap), http_status=dict(status), distinct_bodies=len({r.get("body_sha256") for r in sap}),
                 wall_ms=stats([r["ms"] for r in ok]), model_ms=stats([r["timing_ms"].get("model") for r in ok]),
                 raw_label=dict(Counter(r.get("raw_label") for r in ok))),
    latency_ms_by_host=hosts_ms,
    cache_hits=dict(Counter((r.get("kind"), r.get("src")) and f'{r.get("kind")}:{r.get("src")}' for r in rows if r["host"] == "(disk cache)")),
), indent=1))
