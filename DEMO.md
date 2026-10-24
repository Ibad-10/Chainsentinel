# ChainSentinel: 2-minute demo script

**0:00–0:15 · Opening shot (Live scanner).** Open on **Live scanner**. "This is Ethereum right now: a new block every 12 seconds, a couple of hundred transactions each. Every transaction gets cheap checks; only the suspicious ones go to Sapling, which makes the call." Point at the funnel (*Block #N · 214 txs scanned → 0 suspicious*). If a real hit has come in, open its card. Otherwise press **Inject simulated suspicious tx**: "clearly badged SIMULATED, never counted as real". The card shows the rules, *Sapling is verifying…*, then FLAG with the four scores. Click **Open the real counterparty** to jump into the Bybit exploiter investigation, or go to Overview.

**0:15–0:22 · Hook (Overview).** Switch to the **Overview** dashboard (the live scanner counter is at the top). "Ethereum has no compliance built in: no freeze, no clawback. Lazarus laundered over a billion dollars through it. ChainSentinel lets a compliance analyst see it and decide in seconds. Our rules only gather evidence; Mubit's Banyan Sapling makes the call." Point at the summary: 15 wallets, 10 flagged, 2 review, 3 cleared, and which typologies fired.

**0:12–0:40 · Investigate a real hack (Bybit Exploiter).** Click it under *Start with an example*. The stepper runs: fetch, map the money flow, rules gather evidence, **Sapling verifies**, Sapling scores, verdict. The graph grows out of the exploiter and particles show money moving. Watch the **Sapling verdict** card on the right: it lists what goes in (policy, evidence, claim, about 900 of 16,384 tokens), pulses *Sapling is verifying…*, then reveals the four calibrated scores, the raw status `unsure`, the prediction set and the model time (~1.1 s). "Sapling returns scores, not chat. Its raw status says *ambiguous*, which by Mubit's guidance means route to a human; our FLAG line at 0.60 sits on top, and P(violation) is 0.92."

**0:40–0:55 · Sapling makes the call (counterfactual + policy editor).** Point at *Who makes the call?* right under the verdict: facts alone 70% → facts + rule evidence 92%. Then click **Edit policy and re-run Sapling**, delete the whole line starting `R8 Exploit proceeds` (including its line break, so offline mode hits the cached answer), press **Re-run Sapling**: a live call, about a second, P(violation) drops from 0.92 to 0.64. "Change the policy in plain English and the judgement moves. That's Sapling doing the hard part."

**0:55–1:00 · Plain English.** Hover the dotted *P(violation)* or the **?** next to a rule for a one-line explanation of the jargon.

**1:00–1:15 · No false alarm (Coinbase 10 chip).** "Thousands of transfers, but it's a labelled exchange. The look-alike guard explains it, and Sapling says **CLEAR**." (Binance 14 works the same way.)

**1:15–1:35 · Batch triage.** Click *Run batch triage*: 15 wallets sorted into Flagged / Review / Cleared. "REAL wallets come off the chain. SYNTHETIC ones come from our generator for shapes with no clean public example." Click *Pattern lab*: "Peel chain, scatter-gather, cycle, each drawn and judged."

**1:35–1:55 · Watchlist.** "Watch any public address. We never take keys." Paste a seed phrase to show it gets refused. Click **Simulate suspicious tx**: the alert reads *REVIEW → FLAG, new R2 mixer deposit, R8 exploit proceeds*.

**1:55–2:00 · Close.** "ChainSentinel: graph-first AML where Sapling does the judging. Code is on GitHub."

Prep: run `.venv/bin/python record_scanner.py 12` (records real blocks for the offline scanner replay), then `.venv/bin/python warm_cache.py` and then `.venv/bin/python shoot.py` (which also caches the *R8 removed* policy edit, so the policy-editor step works offline) right before the demo, and start with `CS_OFFLINE=1 ./run.sh` if the wifi is shaky. Add the sweeper wallet `0x8caa5e923374116A4024139bd8382f16A715402c` to the Watchlist beforehand, and press Reset before the simulate step so it starts from REVIEW.
