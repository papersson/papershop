"""SERVICE/load regime: a local HTTP endpoint + an open-loop vegeta adapter.

This is the third measurement regime (library/in-process and CLI/subprocess are
the first two). Its job is to test claim C1 for a load-testing target: can the
SERVICE regime be added with ONLY an adapter, mapping an open-loop generator's
per-request latencies into the EXISTING raw-sample schema, so they flow unchanged
through ``stats.aggregate`` and ``report``?

The adapter does not own the clock or the measurement loop -- vegeta does, exactly
as the CLI regime delegates to hyperfine. It only:

  1. stands up a deterministic, heavy-tailed local endpoint (no external dep),
  2. drives it open-loop at a constant arrival rate with vegeta,
  3. maps each request's latency into the shared raw-sample schema (claim C1/C3):

        {
            "probe":          "http_endpoint",
            "params":         {"rate": R, "duration_s": D},
            "rep":            i,      # request sequence index
            "batch":          1,      # one request == one timed unit of work
            "seconds_per_op": latency_ns / 1e9,
        }

``batch`` is 1 because each request is one complete unit of work that vegeta
times end-to-end (like one process launch in the CLI regime). ``seconds_per_op``
is wall-clock request latency in seconds -- "seconds for one unit of work", the
same unit-agnostic meaning the schema already carries.
"""

from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import sleep

# ---------------------------------------------------------------------------
# The endpoint: a deterministic, seeded, heavy-tailed responder.
# ---------------------------------------------------------------------------
# Each request gets a per-request seed (a monotonic counter) so the induced
# latency distribution is reproducible run to run. The distribution is a mixture:
#   * the common case: ~2 ms of work plus a touch of jitter, and
#   * with probability SPIKE_P: a heavy log-normal spike (tens of ms),
# which guarantees a genuine heavy tail (p99 >> median) on REAL measured data,
# not a synthetic array fed straight to the stats.

SPIKE_P = 0.05
BASE_S = 0.002  # ~2 ms of baseline "work"
JITTER_S = 0.0005  # small uniform jitter so the median CI is well-defined
SPIKE_MU = -3.4  # exp(-3.4) ~= 33 ms median spike
SPIKE_SIGMA = 0.5


def _delay_for(index: int) -> float:
    """Deterministic heavy-tailed service delay (seconds) for request ``index``."""
    rng = random.Random(index)
    delay = BASE_S + rng.uniform(0.0, JITTER_S)
    if rng.random() < SPIKE_P:
        delay += math.exp(SPIKE_MU + SPIKE_SIGMA * rng.gauss(0.0, 1.0))
    return delay


class _Counter:
    def __init__(self) -> None:
        self._n = 0
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            n = self._n
            self._n += 1
        return n


def _make_handler(counter: _Counter):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
            sleep(_delay_for(counter.next()))
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:  # silence per-request logging
            return

    return Handler


class LocalEndpoint:
    """Context-managed local HTTP server on an ephemeral 127.0.0.1 port."""

    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(_Counter()))
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/"

    def __enter__(self) -> "LocalEndpoint":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()


# ---------------------------------------------------------------------------
# The adapter: drive the endpoint open-loop with vegeta, map to raw samples.
# ---------------------------------------------------------------------------


def _vegeta_attack(url: str, rate: int, duration_s: int) -> list[dict]:
    """Run one open-loop, constant-arrival-rate attack; return decoded results.

    vegeta owns the clock and the open-loop scheduling: it fires ``rate``
    requests per second for ``duration_s`` seconds regardless of how fast the
    server replies (this is what avoids coordinated omission, unlike a closed-
    loop tool such as wrk). We capture its binary result stream and decode it to
    one JSON object per request.
    """
    if shutil.which("vegeta") is None:
        raise RuntimeError("vegeta not found on PATH; install it to use this regime")

    target_line = f"GET {url}"
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        bin_path = Path(tmp.name)
    try:
        attack = subprocess.run(
            ["vegeta", "attack", f"-rate={rate}", f"-duration={duration_s}s"],
            input=target_line.encode(),
            stdout=bin_path.open("wb"),
            check=True,
        )
        del attack
        encoded = subprocess.run(
            ["vegeta", "encode", "--to=json", str(bin_path)],
            capture_output=True,
            check=True,
        )
    finally:
        bin_path.unlink(missing_ok=True)

    return [json.loads(line) for line in encoded.stdout.splitlines() if line.strip()]


def correctness_gate(results: list[dict], rate: int) -> dict:
    """Refuse to trust latencies from a run that did not actually serve traffic.

    The SERVICE-regime analogue of the other regimes' output-equality gate: a
    fast latency is meaningless if the requests failed. We require every request
    to return HTTP 200 with no transport error. (A flood of connection errors
    would otherwise masquerade as a suspiciously fast tail.)
    """
    n = len(results)
    bad_code = [r for r in results if r.get("code") != 200]
    errored = [r for r in results if r.get("error")]
    return {
        "rate": rate,
        "n_requests": n,
        "n_non_200": len(bad_code),
        "n_errored": len(errored),
        "passed": n > 0 and not bad_code and not errored,
    }


def collect_samples(url: str, rate: int, duration_s: int) -> tuple[list[dict], dict]:
    """One attack -> (raw samples in the shared schema, correctness-gate result)."""
    results = _vegeta_attack(url, rate, duration_s)
    gate = correctness_gate(results, rate)
    params = {"rate": rate, "duration_s": duration_s}
    samples = [
        {
            "probe": "http_endpoint",
            "params": params,
            "rep": r.get("seq", i),
            "batch": 1,
            "seconds_per_op": r["latency"] / 1e9,  # vegeta latency is nanoseconds
        }
        for i, r in enumerate(results)
    ]
    return samples, gate
