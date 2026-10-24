# ChainSentinel live audit (24 Oct 2026, 05:40–06:19 BST)

**Question:** is ChainSentinel running on live data, calling Banyan Sapling over the network, and meeting the challenge criteria?
**Short answer:** yes, with the exceptions listed under [Still cached, demo or replay](#still-cached-demo-or-replay).

All runs went through the HTTP API of a server started **without** `CS_OFFLINE` and **with** `CS_AUDIT=1`. That setting wraps `requests.Session.request` and writes one JSON line per outbound call to `data/audit.log`: time, feature, host, status, latency, and whether the answer came from the network or the disk cache. For Sapling calls it also records a hash of the request body, `timing_ms` and the label. The raw evidence is in [`docs/audit/`](audit/):

| File | What it holds |
|---|---|
| `audit_summary.json` | `audit_report.py` over every audit log from the session (3,294 events) |
| `runs.json` | final `audit_run.py` pass: investigations, policy editor and batch (06:11–06:14 BST) |
| `runs_before_final_fixes.json` | the earlier pass (05:43 BST), before the last rule fixes |
| `scanner_run.log`, `scanner_state.json` | 11.5-minute live scanner run (05:43:50–05:55:21 BST), 10-second polls and the final state with every card |
| `policy_sensitivity.json` | the same live scanner evidence judged under three policies |
| `sapling_client_tests.json` | 9 failure-mode tests of the Sapling client against a local fake server |
| `sapling_real_error_probes.json` | what the real endpoint returns for bad requests |

Times in the tables below are BST unless marked UTC. Chain timestamps are UTC.

## 1. Outbound calls

| Host | Used for | Calls | Status | Latency min / median / max (ms) |
|---|---|---|---|---|
| `6adbee0669a00298cd4774c9.endpoints.huggingface.cloud` | **Banyan Sapling** | **543** | all HTTP 200 | wall 1,113 / 1,333 / 9,698 · model (`timing_ms.model`) **1,078 / 1,093 / 1,116** |
| `ethereum-rpc.publicnode.com` | scanner blocks, chain head, nonce/balance | 1,511 | network | 35 / 88 / 323 |
| `eth.blockscout.com` | wallet history, tags | 764 | network | 125 / 352 / 8,055 |
| `mempool.space` | Bitcoin history, BTC tip | 261 | network | 32 / 69 / 644 |
| `api.routescan.io` | scanner internal transfers, Blockscout fallback | 180 | network | 42 / 208 / 1,146 |
| disk cache | chain data reused inside the 5-minute TTL | 35 | cache (32 ETH, 3 BTC) | n/a |

- Sapling was called over the network **543 times**, with 131 distinct request bodies. No Sapling answer was served from cache while the endpoint was reachable.
- The gap between wall time and model time is queueing. Batch triage sends Sapling calls back to back, and the endpoint serves them one at a time. A single call on an idle endpoint takes about 1.1 s end to end.
- Model time is about 1.09 s. The model card quotes a 97 ms median on an H200, so this endpoint is on slower hardware.
- Sapling's top labels across all calls: violation 386, insufficient_information 122, supported 35.

### Live vs cached, per feature

| Feature | Chain data | Sapling | Calls in the audit log | On screen |
|---|---|---|---|---|
| Investigate (wallet) | network. A copy is reused for up to 5 min (`CS_CHAIN_TTL`) unless *Live refresh* is on | network on every analysis | 94 Sapling, 156 chain, 22 cache hits | **LIVE** / **CACHED** badge with the newest tx block and time and the chain head |
| Investigate (synthetic case) | generated in `synth.py` (labelled SYNTHETIC) | network | 38 Sapling | SYNTHETIC + LIVE |
| Policy editor | n/a (reuses the evidence) | network | 11 Sapling | "Re-ran live" with model time |
| Batch triage | network (refreshed by *Run batch triage*). Opening the tab reuses a run less than 10 min old, labelled "run at … UTC, reused" | network | 270 Sapling, 330 chain, 13 cache hits | chain and Sapling badge on every card |
| Live scanner | network (RPC blocks + Routescan internal transfers) | network | 1,382 RPC, 210 internal, 18 Sapling | block feed with the source per block |
| Watchlist poller | network | network | 280 chain, 112 Sapling | alerts |
| Label lookups (thread pool) | network | n/a | 358 (logged with feature null) | n/a |

## 2. Investigations, final pass (06:11–06:14 BST)

Every row was fetched from the network through Blockscout, and each row made 2 live Sapling calls (facts only, then facts plus rule findings).

| Wallet | Address | Verdict (facts only) | Rules | P(violation) | Transfers | Newest tx (UTC) | Chain head | Sapling model ms |
|---|---|---|---|---|---|---|---|---|
| Bybit Exploiter | 0x47666F…86E2 | **FLAG** (FLAG) | R3 R4 R8 | 0.908 | 1,761 | #25,292,917, 2026-06-11 08:07 (wallet dormant since then) | #26,260,326 | 1,106 / 1,102 |
| Ronin Bridge Exploiter | 0x098B71…2f96 | **FLAG** (FLAG) | R1 R8 | 0.885 | 1,182 | #26,150,338, 2026-10-08 21:22 | #26,260,327 | 1,103 / 1,108 |
| Coinbase 10 | 0xA9D1e0…3E43 | **CLEAR** (REVIEW) | none | 0.037 | 3,250 | **#26,260,325**, 2026-10-24 05:11, 3 blocks behind the head | #26,260,328 | 1,096 / 1,101 |
| Random sender in head block #26,260,328 (never cached) | 0xf597a4…07c1 | **REVIEW** (REVIEW) | none | 0.209 | 3 | #26,260,327, 2026-10-24 05:11 | #26,260,329 | 1,087 / 1,085 |
| OFAC-listed ETH address, first one in the list with no cache file | 0xf1c4c4…e597 | **FLAG** (FLAG) | R1 | 0.942 | 14 | #25,827,585, 2026-08-24 20:58 | #26,260,329 | 1,088 / 1,091 |

The data is fresh. Coinbase 10's newest transaction is 3 blocks (about 36 s) behind the head when it was fetched, and the random sender's is 1 block behind. The earlier pass (05:43) picked a different random sender and OFAC address. Its random sender came out FLAG on R6 alone (P(v) 0.88), which is a likely false positive; see risks.

**Policy editor** (live, `POST /api/sapling/verify`): Bybit evidence, policy with R2 deleted and a new R9 added. Result: FLAG, P(v) 0.925 against 0.908 with the default policy, model 1,101 ms, 1 attempt, body sha 4b31b7b5…

**Policy sensitivity on a real scanner hit** (`policy_sensitivity.json`). Wallet 0x6bb2f8… sent ETH to Tornado Cash: 1 ETH in block #26,260,196. The evidence and claim stay identical across the three runs; only the policy text changes:

| Policy | Verdict | P(violation) | P(supported) |
|---|---|---|---|
| default | FLAG | 0.882 | 0.036 |
| default with R2 (mixers) deleted | **REVIEW** | **0.357** | 0.106 |
| default plus "R9: any mixer deposit is a violation" | FLAG | 0.855 | 0.043 |

Sapling reads the written policy. Deleting the one rule the evidence matches removes most of the violation probability.

**Batch triage** (live, 104.9 s, 30 Sapling calls, all network). All 8 REAL wallets were refreshed from the network.

| Kind | Wallet | Expected | Verdict | Rules |
|---|---|---|---|---|
| REAL ETH | Ronin, Harmony, Bybit exploiters | violation | FLAG ×3 | R1 R8 · R3 R8 · R3 R4 R8 |
| REAL ETH | Binance 14 hot wallet | supported | CLEAR | none (exchange look-alike) |
| REAL ETH | Coinbase 10 | supported | CLEAR | none |
| REAL ETH | Random sweeper wallet | supported | REVIEW | none (deposit forwarding) |
| REAL BTC | 2 OFAC-listed addresses | violation | FLAG ×2 | R1 |
| SYNTHETIC | peel chain, cycle, chain-hop, mixer layering | violation | FLAG ×4 | |
| SYNTHETIC | scatter-gather, DEX swap layering | violation | REVIEW ×2 | R3 R4 · R3 R6 |
| SYNTHETIC | payroll look-alike | supported | CLEAR | none |

12 of 15 match the expected label. All 3 misses are REVIEW, meaning they go to a human; none is a wrong FLAG or CLEAR.

## 3. Live block scanner (05:43:50–05:55:21 BST, 11.5 min)

The run covered 58 blocks (#26,260,188–#26,260,245) and 10,915 transactions. It found **3,462 internal transfers** via Routescan, plus a few blocks via Blockscout v2. There were 7 suspicious addresses, **7 escalated to Sapling (1 FLAG, 6 REVIEW)**, 0 errors and 0 simulated hits counted. Every escalation made 1 live Sapling call, about 1.08 s each.

| Block | Address | Rule (scanner evidence) | Sapling | P(violation) |
|---|---|---|---|---|
| #26,260,196 | 0x6bb2f8… | R2: 1 ETH into Tornado Cash: 1 ETH | **FLAG** | 0.882 |
| #26,260,201 | 0xae8cbb… | R3 pass-through (forwarded 100% of what it received) | REVIEW | 0.42 |
| #26,260,206 | 0xcfb7e9… | R3 pass-through (100%), from Crypto.com 5 | REVIEW | 0.15 |
| #26,260,225 | 0x465105… | R3 pass-through (100%) | REVIEW | 0.47 |
| #26,260,225 | 0xce5ada… | R3 (forwarded far more than it received) | REVIEW | 0.41 |
| #26,260,238 | 0x743f41… | R3 pass-through (100%) | REVIEW | 0.49 |
| #26,260,243 | 0xa9ac43… | R3 ×2 (3,772% and 145% of what it received) | REVIEW | 0.45 |

The stage-1 rules raised 7 hits and Sapling escalated only the mixer deposit to FLAG; it held the weak pass-through hits at REVIEW. Two of the R3 hits were wallets sending far more than they had received, so they were funded wallets, not pass-throughs. R3 now requires 80–125% of what came in to go out, which removes those two.

## 4. Sapling contract and failure handling

- **Request:** `POST {"inputs": {"policy", "evidence", "claim"}}`, all non-empty (checked before sending). The size estimate is characters ÷ 2.2, with a refusal at 95% of 16,384. The ratio was measured on the real endpoint, which counted 33,394 tokens for about 72k characters. The old ÷ 3.2 estimate under-counted by about 45%. Typical audited requests were 1,100–1,500 tokens.
- **Response:** `status`, `raw_label`, `prediction_set`, all 4 `probabilities` (checked to be numbers), and `timing_ms`. Every result in the audited runs had `status: "unsure"`. ChainSentinel shows that raw status next to its own cut-offs.
- **Real error behaviour** (`sapling_real_error_probes.json`):
  - An empty field comes back as **HTTP 200** with `{"error": …}`. The old client would have turned this into an all-empty result; the new one raises a clear error.
  - A missing `inputs` wrapper gives 400.
  - An oversized request gives 400 "no truncation".
- **Retries** (`backend/sapling_client.py`):
  - Retried with exponential backoff (2 s doubling, capped at 20 s) within a 75 s deadline: timeout, connection error, 429, 502/503/504 (an HF scale-to-zero cold start), and malformed 200s.
  - Other 4xx errors fail at once.
  - Every result records `attempts`, `request_sha256` and `http_status`.
- **Tests:** 9 of 9 pass against a local fake server (`tests/test_sapling_client.py`): request shape, parsing, cold start 503 → 503 → 200 in 3 attempts, 429, 400 with no retry, malformed response, still cold at the deadline, timeout, unreachable.
- **Sapling unreachable, in the UI** (server pointed at a closed port):
  - With a stored answer for that exact evidence, the result is badged **CACHE FALLBACK**. It reads "Sapling unreachable, showing its earlier answer to this exact evidence (N min old)", and the verdict header says "Earlier answer · Sapling unreachable now" instead of "Verified live" (`screenshots/21_…`).
  - Without one, there is no verdict. The page reads "The chain data was fetched, but Sapling could not be reached, so there is no verdict: ChainSentinel never makes the call without Sapling" (`screenshots/22_…`).
  - This test found a JS error ("reading 'cy'" when a failed investigation replaced a graph mid-animation). It is fixed, and the rerun showed no page errors.

## 5. Criteria scorecard

| Criterion | Score | Evidence | Gaps |
|---|---|---|---|
| **(a) Best use case of Sapling** | Strong | - The model card's target is policy checks, evidence review and claim validation, with "retrieval, source authentication, generated explanations, and final business decisions" left to the surrounding workflow. ChainSentinel uses it that way: deterministic code fetches and cites the chain evidence, a written 8-rule AML policy is the `policy`, one claim is tested, and Sapling's calibrated scores make the call.<br>- It uses all of Sapling's outputs (4 probabilities, `status`, `prediction_set`, `timing_ms`).<br>- Requests run to about 1.1–1.5k tokens, well inside the limit. | - Sapling's own `status` was `unsure` on every audited result, so the FLAG/CLEAR line comes from our cut-offs on its probabilities. This is disclosed in the UI and README, but Sapling's calibrated decision never resolves on its own here.<br>- Not fixable on our side. |
| **(b) Sapling does the hard part, not a chat box** | Strong | - No chat UI and no LLM: one structured API call.<br>- The verdict is a function of Sapling's probabilities only; rules never set it.<br>- Deleting R2 from the policy moves a real Tornado deposit from FLAG 0.88 to REVIEW 0.36 with identical evidence.<br>- In the scanner, 7 rule hits became 1 FLAG and 6 REVIEW.<br>- Coinbase 10 goes from REVIEW on facts alone to CLEAR once the look-alike evidence is in. | - The readable "why" paragraph is template text written by our code. It is labelled as such, because Sapling returns no explanations.<br>- Rule findings steer Sapling, so a wrong finding can mislead it. Audit fix: the R6 swap finding used to assert "no business purpose … funds leave to a fresh wallet" without checking. It now states only checked facts, and the synthetic DEX case dropped from FLAG to REVIEW (P(v) 0.46) as a result. |
| **(c) A demo where we watch it work on a realistic input** | Strong | - Live mainnet scanner: 58 blocks and 10,915 txs in 11.5 min, with 7 real escalations including a real Tornado Cash deposit flagged live.<br>- Real exploiter wallets refreshed live.<br>- A random address from the head block and a never-cached OFAC address.<br>- A live/cached badge on every result.<br>- The pipeline stepper animates on the real model time. | - Real blocks are mostly clean, so a short demo may need the SIMULATED inject, which is labelled.<br>- The scanner's per-address evidence is thin by design: a 50-block window. |
| **Entry: video ≤ 2 min or screenshots, repo link** | Partly done | - 22 screenshots in `screenshots/`, re-taken in this audit against the live server.<br>- `docs/demo_silent.mp4`: a 78-second silent screen capture of the live app (`record_demo.py`): Overview, Bybit live (FLAG), the policy editor re-run, Coinbase 10 (CLEAR), the scanner, then batch.<br>- `DEMO.md` is the narration script. | - The video has no voice-over or captions. Its scanner segment shows the SIMULATED card left by the screenshot run, which is badged on screen.<br>- **Repo link pending**: nothing has been pushed. |

## 6. Fixes made in this audit

1. **Silent cache, fixed.** Cached chain data used to be served forever, and failures fell back to cache silently. Now chain data is reused for at most 5 min (`CS_CHAIN_TTL`), and every result carries provenance: `network` / `cache` / `cache-fallback` (with the error) / `replay`. Sapling is always called live online; its stored answer is only a labelled fallback when the endpoint is down.
2. **Freshness.** Wallet history used to be the *oldest* 1,000 transfers, sorted ascending, so a busy wallet never showed recent activity. It is now the newest 1,000 plus the earliest 500 when capped. Each result reports the newest block and time against the chain head.
3. **Blockscout outages.** Blockscout returned 503 for part of the session. There is now a Routescan fallback and a 60 s circuit breaker per host.
4. **Scanner internal transfers stuck at 0.** Blockscout indexes them 25+ blocks late. Routescan is now the primary source (within about 20 s), and blocks still empty after 10 min are counted as *internal unavailable*.
5. **Sapling client rewritten.** It handles HTTP 200 `{error}` replies, checks the response, retries with backoff and has a deadline. There are 9 tests.
6. **Token estimate** corrected from characters ÷ 3.2 to ÷ 2.2, measured on the real endpoint.
7. **Batch triage** now refreshes chain data when run, and reports `ran_at`, `run_ms` and whether it was reused.
8. **UI:** LIVE / CACHED / CACHE FALLBACK / REPLAY badges per result and per batch card. The verdict header says "Verified live" only for live calls. The no-Sapling error page no longer says "Nothing was sent". The null-graph JS error is fixed.
9. **Rule false positives seen on live data:**
   - Scanner R3 now needs 80–125% of the inflow forwarded.
   - An exchange-labelled wallet's DEX swaps and bridge transfers are treated as routine. This is why Binance 14 moved from FLAG to CLEAR.
   - The unverified R6 swap wording is replaced with checked facts.
10. **BTC newest block** was missing for some addresses and is now filled from `status.block_height`.

## 7. Remaining risks

- Sapling's `status` is always `unsure` on these inputs, so the cut-offs carry the decision.
- The endpoint runs about 11× slower than the model card's reference. A cold HF endpoint can take more than a minute, which the 75 s deadline covers only partly.
- Rules on random live wallets still misfire sometimes. In the 05:43 pass, an R6-only bridge hit gave FLAG 0.88. In earlier runs, R3 alone gave REVIEW–FLAG on ordinary senders.
- Routescan and publicnode are free third-party tiers with no SLA, and Blockscout was down for part of this session.
- Transfer counts move slightly between runs (Bybit: 1,766 in the 05:43 pass, 1,761 at 06:11) because the newest-1,000 window shifts.
- The watchlist poller made 112 Sapling calls in about 40 minutes on 2 watched wallets: real load on the endpoint.
- Label lookups run in worker threads and are logged with `feature: null`.

## Still cached, demo or replay

- **Pattern lab and the synthetic batch cards** use generated transactions (`synth.py`), labelled SYNTHETIC. Their Sapling calls are live.
- **"Inject simulated suspicious tx"** (scanner) and **"Simulate suspicious tx"** (watchlist) are made-up scenarios, labelled SIMULATED and kept out of the real totals.
- **`CS_OFFLINE=1`** replays recorded blocks and cached Sapling answers, labelled REPLAY. It was not used in this audit.
- Chain data within 5 minutes of a previous fetch is served from disk, labelled CACHED with its age. Tick *Live refresh* to bypass it.
- Opening the Batch tab within 10 minutes of a run reuses that run, labelled "run at … UTC, reused". The *Run batch triage* button always runs live.
- The README's old "Results snapshot (cached run)" table is replaced by the batch table above.
