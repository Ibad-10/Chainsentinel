"""Record a session of real blocks for the offline scanner replay, then warm the Sapling cache for it.
Run online:  .venv/bin/python record_scanner.py [n_blocks]"""
import sys, time
sys.path.insert(0, "backend")
import scanner as S
rec = S.record(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
sc = S.Scanner(); sc.mode = "replay"; sc.recording = rec; sc.ri = 0
S.time_sleep = time.sleep
for _ in rec["blocks"]: sc.step_replay()
sc.inject()
while sc.inflight: time.sleep(0.5)
st = sc.state()
print("replay warm:", st["totals"], "simulated:", st["simulated"])
for c in st["cards"]: print(c["block"], c["status"], [r["id"] for r in c["rules"]], c.get("verdict"), c.get("error"))
