"""SYNTHETIC EVM-style transaction generator (clearly labelled, no real addresses).
Shapes follow IBM AMLworld typologies (Altman et al., NeurIPS 2023) plus crypto-specific ones.
Adapted from /workspace/aml/synth.py; each case returns (wallet, txs, labels)."""
import random
T0 = 1761200000
def _rng(seed): return random.Random(seed)
def _addr(r): return "0x" + "".join(r.choice("0123456789abcdef") for _ in range(40))
def _tx(f, t, v, ts, asset="ETH"): return dict(frm=f, to=t, value=round(v, 4), ts=ts, asset=asset)
NAMED = {
 "0xthorchainrouter000000000000000000000000": ("THORChain Router (synthetic)", "bridge"),
 "0xavalanchebridge000000000000000000000000": ("Avalanche Bridge (synthetic)", "bridge"),
 "0xuniswaprouter0000000000000000000000000": ("Uniswap Router (synthetic)", "dex"),
 "0xbinancedeposit0000000000000000000000000": ("Binance deposit (synthetic)", "exchange"),
 "0xcoinbasecustody00000000000000000000000": ("Coinbase Custody (synthetic)", "exchange"),
 "0xhackerwallet00000000000000000000000000": ("Bridge Exploiter (synthetic)", "exploit"),
 "0xtornado100eth0000000000000000000000000": ("Tornado Cash 100 ETH pool (synthetic)", "mixer"),
}
N = {v[0].split(" (")[0]: k for k, v in NAMED.items()}
def peel_chain(n=10):
    r = _rng(1); a = _addr(r); txs = [_tx(_addr(r), a, 250, T0)]; cur = a; bal = 250; ts = T0
    for _ in range(n):
        ts += r.randint(600, 3000); nxt = _addr(r); peel = round(r.uniform(2, 6), 3); bal -= peel + 0.002
        txs += [_tx(cur, _addr(r), peel, ts), _tx(cur, nxt, bal, ts + 5)]; cur = nxt
    return a, txs
def scatter_gather(k=12):
    r = _rng(2); a = _addr(r); dst = _addr(r); txs = [_tx(_addr(r), a, 240, T0)]; ts = T0
    mids = [_addr(r) for _ in range(k)]
    for m in mids: ts += 120; txs.append(_tx(a, m, 19.9, ts))
    for m in mids: ts += 300; txs.append(_tx(m, dst, 19.88, ts))
    return a, txs
def cycle():
    r = _rng(3); a = _addr(r); b, c, d = _addr(r), _addr(r), _addr(r); ts = T0
    return a, [_tx(_addr(r), a, 80, ts), _tx(a, b, 80, ts + 900), _tx(b, c, 79.9, ts + 2000), _tx(c, d, 79.8, ts + 4000),
               _tx(d, a, 79.7, ts + 7000), _tx(a, N["Binance deposit"], 79.6, ts + 9000)]
def chain_hop():
    r = _rng(4); a = _addr(r); ts = T0
    return a, [_tx(N["Bridge Exploiter"], a, 500, ts), _tx(a, N["THORChain Router"], 250, ts + 1800), _tx(a, N["Avalanche Bridge"], 249, ts + 2600)]
def mixer_layering():
    r = _rng(5); a = _addr(r); ts = T0; txs = [_tx(N["Bridge Exploiter"], a, 600, ts)]
    hops = [_addr(r) for _ in range(3)]
    for i, h in enumerate(hops):
        txs.append(_tx(a, h, 200, ts + 600 * (i + 1)))
        txs.append(_tx(h, N["Tornado Cash 100 ETH pool"], 100, ts + 600 * (i + 1) + 300))
        txs.append(_tx(h, N["Tornado Cash 100 ETH pool"], 100, ts + 600 * (i + 1) + 360))
    return a, txs
def dex_layering():
    r = _rng(6); a = _addr(r); ts = T0; txs = [_tx(_addr(r), a, 120, ts)]
    for i, (p, q) in enumerate([("ETH", "USDC"), ("USDC", "DAI"), ("DAI", "WBTC"), ("WBTC", "ETH"), ("ETH", "USDT")]):
        txs.append(_tx(a, N["Uniswap Router"], 120 if p == "ETH" else 0.0, ts + 600 * (i + 1), asset=f"swap {p}->{q}"))
    txs.append(_tx(a, _addr(r), 119, ts + 5000, asset="USDT"))
    return a, txs
def payroll_lookalike(k=20):
    r = _rng(7); a = _addr(r); ts = T0; txs = []; emps = [_addr(r) for _ in range(k)]
    for m in range(4):
        txs.append(_tx(N["Coinbase Custody"], a, 30, ts + m * 30 * 86400))
        for i, e in enumerate(emps): txs.append(_tx(a, e, 1.4 + 0.01 * i, ts + m * 30 * 86400 + 86400))
    return a, txs
CASES = {
 "peel_chain": ("Peel chain", peel_chain, "violation"),
 "scatter_gather": ("Scatter-gather", scatter_gather, "violation"),
 "cycle_round_trip": ("Cycle / round-trip", cycle, "violation"),
 "chain_hop_bridge": ("Chain-hop via bridge", chain_hop, "violation"),
 "mixer_layering": ("Mixer layering (Tornado via hops)", mixer_layering, "violation"),
 "dex_swap_layering": ("DEX swap layering", dex_layering, "violation"),
 "payroll_lookalike": ("Payroll look-alike (legit)", payroll_lookalike, "supported"),
}
