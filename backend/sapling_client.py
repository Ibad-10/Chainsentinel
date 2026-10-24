import requests, time
URL="https://6adbee0669a00298cd4774c9.endpoints.huggingface.cloud"
POLICY="""Crypto AML policy (EVM and Bitcoin wallets). A wallet VIOLATES this policy if ANY rule below is met:
R1 Sanctions: it sends to or receives from an OFAC-sanctioned address, or is itself on the OFAC SDN list.
R2 Mixers: it deposits funds into a mixer or privacy pool (e.g. Tornado Cash, Sinbad, Blender), especially in fixed denominations (0.1/1/10/100 ETH).
R3 Rapid pass-through: it forwards more than 80% of received funds within 24 hours of receiving them.
R4 Fan-out / splitting: a large inflow is split into many (10+) transfers to fresh addresses, or into near-identical amounts.
R5 Peel chain: a long run of transactions each sending a small amount out and passing the large remainder to a new address.
R6 Chain-hopping: funds are moved to a cross-chain bridge or swap service (e.g. THORChain, Avalanche bridge, renBridge) soon after receipt with no business purpose.
R7 Round-tripping / cycles: funds return to the origin address through intermediate wallets.
R8 Exploit proceeds: the wallet is labelled as a hack, exploit, scam or phishing address.
Legitimate look-alikes that do NOT violate on their own: exchange hot wallets, payroll, merchants and market makers, which show high volume with many known counterparties and steady, long-running activity.
A wallet is COMPLIANT only if none of R1-R8 are met and its activity is explained."""
CLAIM="This wallet's activity is consistent with legitimate use and complies with the AML policy."
def check(evidence, claim=CLAIM, policy=POLICY):
    for i in range(3):
        try:
            r=requests.post(URL,json={"inputs":{"policy":policy,"evidence":evidence,"claim":claim}},timeout=90)
            d=r.json(); return {k:d.get(k) for k in ["status","raw_label","prediction_set","probabilities","timing_ms"]}
        except Exception as e: err=str(e); time.sleep(3)
    return {"error":err}
