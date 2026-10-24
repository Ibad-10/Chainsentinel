# Draft social posts (DRAFTS ONLY, not posted)

## X
Built ChainSentinel at #NightShift 🛰️ on-chain AML where @MubitLabs Banyan Sapling makes the call.

Paste an ETH/BTC address → live money-flow graph → 8 laundering detectors (mixers, peel chains, bridge hops, fan-out, OFAC) → Sapling judges the evidence against an AML policy → FLAG / REVIEW / CLEAR, with every flow highlighted.

Real Lazarus wallets (Ronin, Harmony, Bybit) get flagged. Binance's hot wallet gets cleared.

🎥 [demo video]  💻 [repo link]

## LinkedIn
At Mubit's Night Shift hackathon in London I built **ChainSentinel**, an on-chain anti-money-laundering triage tool powered by Mubit's **Banyan Sapling** semantic verification model.

**The task:** a compliance analyst gets an Ethereum or Bitcoin address and has to decide fast: is this laundering, or a legitimate look-alike like an exchange or payroll wallet?

**How it works:**
• Pulls the address's real transactions from public explorers (Blockscout, mempool.space)
• Draws an interactive money-flow graph coloured by entity type (exploit, OFAC-sanctioned, mixer, bridge, exchange)
• Runs 8 deterministic detectors: sanctions exposure, mixer deposits, rapid pass-through, fan-out/scatter-gather, peel chains, chain-hopping, round-trips, exploit proceeds
• Sends the policy, evidence and claim to Banyan Sapling, which returns calibrated probabilities that map to FLAG / REVIEW / CLEAR
• Explains every verdict: the rules that fired (click to highlight the exact flows), a plain-English "why", a facts-only vs facts-plus-findings counterfactual, and the exact text Sapling saw

On real data it flags the Ronin, Harmony and Bybit exploiter wallets and clears Binance's hot wallet. A Pattern Lab of clearly labelled synthetic typologies covers shapes with no clean public example, and a Watchlist alerts when a tracked wallet's verdict changes.

Demo: [video link] · Code: [repo link]

Thanks to Mubit for the model and the night shift ☕ #AML #Ethereum #Bitcoin #AI #Hackathon
(tag: Mubit)
