# ChainSentinel: 2-minute demo script

**0:00–0:12 · Hook.** "Ethereum has no compliance built in: no freeze, no clawback. Lazarus laundered over a billion dollars through it. ChainSentinel lets a compliance analyst see it and decide in seconds. Our rules detect, Mubit's Banyan Sapling decides."

**0:12–0:45 · Investigate a real hack (Bybit Exploiter chip).** The graph builds from live Blockscout data. "Yellow is the exploiter; edges are sized by ETH." Click **R4 Fan-out**: the split into fresh wallets lights up. Point at the verdict: **FLAG**, P(violation) 91%. Open *Exactly what Sapling saw*: "This is the policy, evidence and claim. No chat box, one call, about a second."

**0:45–1:00 · Counterfactual.** Point at the two columns. "On raw facts Sapling holds back. Once our detectors cite the specific transactions, it commits. Every claim is checkable on the graph."

**1:00–1:15 · No false alarm (Binance 14 chip).** "Thousands of transfers and huge fan-out, but it's a labelled exchange. The look-alike guard explains it, and Sapling says **CLEAR**."

**1:15–1:35 · Batch triage.** Click *Run batch triage*: 15 wallets sorted into Flagged / Review / Cleared in a few seconds. "REAL wallets come off the chain. SYNTHETIC ones come from our generator for shapes with no clean public example." Click *Pattern lab*: "Peel chain, scatter-gather, cycle, each drawn and judged."

**1:35–1:55 · Watchlist.** "Watch any public address. We never take keys." Click **Simulate suspicious tx**: the alert reads *REVIEW → FLAG, new R2 mixer deposit, R8 exploit proceeds*.

**1:55–2:00 · Close.** "ChainSentinel: graph-first AML where Sapling does the judging. Code is on GitHub."

Prep: run `.venv/bin/python warm_cache.py`, start with `CS_OFFLINE=1 ./run.sh` if the wifi is shaky, and add the sweeper wallet `0x8caa5e923374116A4024139bd8382f16A715402c` to the Watchlist beforehand. Before the simulate step, press Reset so it starts from REVIEW.
