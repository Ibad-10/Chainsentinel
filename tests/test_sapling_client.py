"""Sapling client error handling against a local fake endpoint: cold start (503 then 200), 4xx, malformed, timeout, unreachable.
Run: .venv/bin/python tests/test_sapling_client.py"""
import sys, os, json, threading, time, http.server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import sapling_client as SC
OK = {"status": "violation", "raw_label": "violation", "prediction_set": ["violation"], "timing_ms": {"model": 1000.0},
      "probabilities": {"supported": .05, "violation": .9, "insufficient_information": .04, "inconsistent_context": .01}}
PLAN = []; SEEN = []
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append(body); code, payload, delay = PLAN.pop(0) if PLAN else (200, OK, 0)
        time.sleep(delay)
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(payload.encode() if isinstance(payload, str) else json.dumps(payload).encode())
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
SC.URL = f"http://127.0.0.1:{srv.server_port}"
def expect_error(kind, **kw):
    try: SC.check("evidence", **kw); raise AssertionError("expected an error")
    except SC.SaplingError as e: assert e.kind == kind, (e.kind, str(e)); return str(e)
results = []
def case(name, fn):
    t0 = time.time(); out = fn(); results.append((name, round(time.time() - t0, 1), out)); print(f"PASS {name} ({time.time() - t0:.1f}s): {str(out)[:110]}")
# request shape: {"inputs": {policy, evidence, claim}}, all non-empty
case("request shape", lambda: (SC.check("some evidence"), SEEN[-1]["inputs"].keys() == {"policy", "evidence", "claim"} and all(SEEN[-1]["inputs"].values()) or (_ for _ in ()).throw(AssertionError(SEEN[-1])))[1])
case("parses status/raw_label/prediction_set/probabilities/timing_ms", lambda: sorted(SC.check("e").keys()))
PLAN[:] = [(503, "<html>503 Service Temporarily Unavailable</html>", 0), (503, {"error": "Service Unavailable"}, 0), (200, OK, 0)]
case("cold start: 503, 503, then 200 -> retried with backoff", lambda: SC.check("e")["attempts"])
PLAN[:] = [(429, {}, 0), (200, OK, 0)]
case("429 -> retried", lambda: SC.check("e")["attempts"])
PLAN[:] = [(400, {"error": "Input exceeds 16384 tokens"}, 0)]
case("400 -> fails at once, no retry", lambda: expect_error("client_error"))
PLAN[:] = [(200, {"status": "x"}, 0)] * 10
case("malformed 200 (no probabilities) -> error", lambda: expect_error("malformed", deadline=3))
PLAN[:] = [(503, "{}", 0)] * 20
case("endpoint stays cold -> gives up at the deadline", lambda: expect_error("cold_start", deadline=7))
SC.READ_TIMEOUT = 1; PLAN[:] = [(200, OK, 2)] * 5
case("timeout (server takes 2 s, client waits 1 s) -> retried, then gives up", lambda: expect_error("timeout", deadline=4))
SC.READ_TIMEOUT = 90; SC.URL = "http://127.0.0.1:9"
case("unreachable -> gives up at the deadline", lambda: expect_error("unreachable", deadline=4))
srv.shutdown()
json.dump([dict(test=n, secs=s, result=str(o)[:200]) for n, s, o in results], open(os.path.join(os.path.dirname(__file__), "..", "docs", "audit", "sapling_client_tests.json"), "w"), indent=1)
print("all", len(results), "passed")
