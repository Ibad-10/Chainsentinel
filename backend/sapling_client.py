import requests, time, json, hashlib, os
URL = os.environ.get("CS_SAPLING_URL", "https://6adbee0669a00298cd4774c9.endpoints.huggingface.cloud")
READ_TIMEOUT = float(os.environ.get("CS_SAPLING_TIMEOUT", "90"))  # seconds to wait for one answer
DEADLINE = float(os.environ.get("CS_SAPLING_DEADLINE", "75"))  # total seconds to keep retrying (covers an HF scale-from-zero cold start)
LABELS = ("supported", "violation", "insufficient_information", "inconsistent_context")
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
class SaplingError(RuntimeError):
    def __init__(self, msg, kind): super().__init__(msg); self.kind = kind

def parse(d):
    """Validate a Sapling response: status, raw_label, prediction_set, probabilities (all 4 labels), timing_ms."""
    if isinstance(d, list) and d: d = d[0]
    if not isinstance(d, dict): raise SaplingError("Sapling returned something that is not a JSON object.", "malformed")
    if d.get("error"): raise SaplingError(f"Sapling error: {str(d['error'])[:200]}", "server")
    p = d.get("probabilities")
    if not isinstance(p, dict) or not all(isinstance(p.get(k), (int, float)) for k in LABELS):
        raise SaplingError("Sapling response is missing the four label probabilities.", "malformed")
    return {"status": d.get("status"), "raw_label": d.get("raw_label"), "prediction_set": d.get("prediction_set") or [],
            "probabilities": {k: float(p[k]) for k in LABELS}, "timing_ms": d.get("timing_ms") or {}}

def check(evidence, claim=CLAIM, policy=POLICY, deadline=None):
    """POST {"inputs": {policy, evidence, claim}} to the Sapling endpoint. Retries with exponential backoff on
    timeouts, connection errors, 429 and 5xx (an HF endpoint that scaled to zero answers 502/503 while it wakes).
    Other 4xx fail at once. Returns the parsed result plus attempts/request sha; raises SaplingError."""
    body = json.dumps({"inputs": {"policy": policy, "evidence": evidence, "claim": claim}})
    sha = hashlib.sha256(body.encode()).hexdigest()[:16]
    t0 = time.time(); delay = 2.0; attempt = 0; deadline = DEADLINE if deadline is None else deadline
    while True:
        attempt += 1
        try:
            r = requests.post(URL, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=(10, READ_TIMEOUT))
        except requests.Timeout: err, kind = "Sapling did not answer in time (timeout).", "timeout"
        except requests.ConnectionError: err, kind = "Sapling endpoint unreachable (connection failed).", "unreachable"
        else:
            if r.status_code == 200:
                try: out = parse(r.json())
                except ValueError: out = None; err, kind = "Sapling returned non-JSON.", "malformed"
                except SaplingError as e: out = None; err, kind = str(e), e.kind
                if out is not None:
                    out.update(attempts=attempt, request_sha256=sha, http_status=200); return out
                if kind == "server": raise SaplingError(err, kind)
            elif r.status_code in (502, 503, 504):
                err, kind = f"Sapling endpoint is starting up or overloaded (HTTP {r.status_code}). An HF endpoint that scaled to zero takes a minute or more to wake.", "cold_start"
            elif r.status_code == 429: err, kind = "Sapling rate limit hit (HTTP 429).", "rate_limited"
            else:
                raise SaplingError(f"Sapling rejected the request (HTTP {r.status_code}): {r.text[:160]}", "client_error")
        if time.time() - t0 + delay > deadline:
            raise SaplingError(f"{err} Gave up after {attempt} attempts over {int(time.time() - t0)} s.", kind)
        time.sleep(delay); delay = min(delay * 2, 20)
