"""Pre-fetch every showcase wallet and Sapling response into ./cache so the demo works offline (CS_OFFLINE=1)."""
import sys; sys.path.insert(0, "backend")
import engine as E, showcase as S
for c in S.REAL:
    r = E.analyze(c["chain"], c["address"]); print(r["verdict"], [x["id"] for x in r["rules"]], c["title"])
for k in E.SY.CASES:
    r = E.analyze("eth", None, synthetic_case=k); print(r["verdict"], [x["id"] for x in r["rules"]], k)
E.save_labels()
