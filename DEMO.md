# ChainSentinel: 2-minute demo script

**0:00–0:12 · Hook (Overview).** Open on the **Overview** dashboard. "Ethereum has no compliance built in: no freeze, no clawback. Lazarus laundered over a billion dollars through it. ChainSentinel lets a compliance analyst see it and decide in seconds. Our rules detect, Mubit's Banyan Sapling decides." Point at the summary: 15 wallets, 10 flagged, 2 review, 3 cleared, and which typologies fired.

**0:12–0:45 · Investigate a real hack (Bybit Exploiter).** Click it under *Start with an example*. The six-step stepper runs: fetch, build graph, rules fire, ask Sapling, probabilities, cut-offs. The graph grows out of the exploiter, and particles show money moving, sized by value. Click step **3 Rules fire**: the flows behind R3, R4 and R8 light up and the 39 fresh wallets glow as one group. Point at the verdict: **FLAG**, P(violation) 92%. Click step **4 Ask Sapling**: "This is the policy, evidence and claim. No chat box, one call, about a second."

**0:45–1:00 · How it works.** Open **How it works** and scroll to the counterfactual. "On raw facts Sapling says 70% violation. Once our detectors cite the specific transactions, it goes to 92%. Every claim is checkable on the graph, and the cut-offs are fixed and visible."

**1:00–1:15 · No false alarm (Coinbase 10 chip).** "Thousands of transfers, but it's a labelled exchange. The look-alike guard explains it, and Sapling says **CLEAR**." (Binance 14 works the same way.)

**1:15–1:35 · Batch triage.** Click *Run batch triage*: 15 wallets sorted into Flagged / Review / Cleared. "REAL wallets come off the chain. SYNTHETIC ones come from our generator for shapes with no clean public example." Click *Pattern lab*: "Peel chain, scatter-gather, cycle, each drawn and judged."

**1:35–1:55 · Watchlist.** "Watch any public address. We never take keys." Paste a seed phrase to show it gets refused. Click **Simulate suspicious tx**: the alert reads *REVIEW → FLAG, new R2 mixer deposit, R8 exploit proceeds*.

**1:55–2:00 · Close.** "ChainSentinel: graph-first AML where Sapling does the judging. Code is on GitHub."

Prep: run `.venv/bin/python warm_cache.py` right before the demo, and start with `CS_OFFLINE=1 ./run.sh` if the wifi is shaky. Add the sweeper wallet `0x8caa5e923374116A4024139bd8382f16A715402c` to the Watchlist beforehand, and press Reset before the simulate step so it starts from REVIEW.
