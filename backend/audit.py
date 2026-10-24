"""CS_AUDIT=1: log every outbound HTTP call (and every cache answer) to data/audit.log as JSON lines.
Each line: ts, host, path, method, status, ms, bytes, src (network | cache | replay | cache-fallback), plus
for Sapling the request-body sha256 and the response's timing_ms. Nothing secret is logged: no headers, no bodies."""
import os, json, time, hashlib, threading, urllib.parse, requests

ON = os.environ.get("CS_AUDIT") == "1"
PATH = "/tmp/chainsentinel-audit.log" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "audit.log")
_lock = threading.Lock()
CTX = threading.local()  # .feature: which feature made the call (set by app.py per request)

def write(**rec):
    if not ON: return
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "t": round(time.time(), 3), "feature": getattr(CTX, "feature", None), **rec}
    try:
        with _lock, open(PATH, "a") as f: f.write(json.dumps(rec) + "\n")
    except Exception: pass

def cache_hit(kind, key_sha, src, age_s):
    write(host="(disk cache)", kind=kind, key=key_sha[:12], src=src, age_s=None if age_s is None else int(age_s))

_orig = requests.Session.request
def _request(self, method, url, **kw):
    t0 = time.time(); u = urllib.parse.urlsplit(url); status = None; nbytes = 0; extra = {}
    body = kw.get("data") if kw.get("data") is not None else (json.dumps(kw["json"]) if kw.get("json") is not None else None)
    if "huggingface.cloud" in u.netloc and body is not None:
        extra["body_sha256"] = hashlib.sha256(body.encode() if isinstance(body, str) else body).hexdigest()[:16]
    try:
        r = _orig(self, method, url, **kw); status = r.status_code; nbytes = len(r.content or b"")
        if "huggingface.cloud" in u.netloc:
            try:
                d = r.json(); d = d[0] if isinstance(d, list) else d
                extra["timing_ms"] = d.get("timing_ms"); extra["raw_label"] = d.get("raw_label")
            except Exception: extra["resp_head"] = (r.text or "")[:80]
        return r
    except Exception as e:
        extra["error"] = type(e).__name__; raise
    finally:
        q = urllib.parse.parse_qs(u.query); act = (q.get("action") or q.get("module") or [""])[0]
        write(host=u.netloc, path=(u.path[:60] + (f"?action={act}" if act else "")), method=method, status=status,
              ms=int((time.time() - t0) * 1000), bytes=nbytes, src="network", **extra)
if ON: requests.Session.request = _request
