"""The CLI/subprocess regime: measure external commands by wrapping hyperfine.

This is the second measurement regime (the first is the in-process library
runner in ``core.py``). Its whole reason to exist is to test the normalization
hypothesis (claim C3): can a single raw-sample schema ingest measurements
produced by a *foreign* benchmarking tool — here hyperfine — rather than our own
timing loop?

The answer is yes, and this module is the evidence. It does NOT re-implement the
clock, warmup, or repetition machinery; hyperfine already owns those. It only:

  1. enforces a correctness gate across the commands being compared (claim C5),
  2. shells out to ``hyperfine --export-json`` with a warmup and a run count,
  3. maps hyperfine's per-command ``times`` array into the EXISTING raw-sample
     schema that ``stats.aggregate`` and ``report.plot_scaling`` already read.

Raw-sample schema emitted (identical to ``core.run_suite`` — the load-bearing
contract that lets the rest of the spine stay untouched):

    {
        "probe":          str,    # the command label
        "params":         dict,   # the input point (e.g. {"lines": 10000})
        "rep":            int,    # which hyperfine run this came from
        "batch":          1,      # hyperfine times one whole invocation at a time
        "seconds_per_op": float,  # wall-clock seconds for that one invocation
    }

Why ``batch`` is always 1: hyperfine measures wall-clock time of a complete
process launch + run, one invocation per timed sample. There is no sub-call
batching to calibrate (unlike the in-process runner, where a single function
call can be faster than the clock's resolution). Each element of hyperfine's
``times`` array is already one operation, so ``seconds_per_op`` is that element
verbatim and ``batch`` is 1. The schema absorbs this difference with no change.

Mapping note for honesty: ``seconds_per_op`` here is whole-process wall-clock
time (includes interpreter/process startup), whereas in the library regime it is
in-process call time. Both are "seconds for one unit of work" — the schema is
unit-agnostic, which is exactly the property C3 predicts.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class CliProbe:
    """A command variant under test. Analogue of ``core.Probe`` for the shell.

    ``command(params)`` returns the full shell command line to benchmark for a
    given input point. Two probes are comparable when, for the same params, they
    produce equivalent (normalized) stdout — the correctness gate enforces this.
    """

    name: str
    command: Callable[[dict], str]  # params -> shell command line


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _default_normalize(stdout: str) -> str:
    """Conservative default: ignore only trailing whitespace differences."""
    return stdout.strip()


def _capture(command: str) -> str:
    """Run ``command`` through the shell exactly as hyperfine will, grab stdout."""
    proc = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command exited {proc.returncode} during correctness gate: "
            f"{command!r}\nstderr: {proc.stderr.strip()}"
        )
    return proc.stdout


def run_cli_suite(
    probes: list[CliProbe],
    param_grid: list[dict],
    *,
    prepare: Callable[[dict], Any] | None = None,
    normalize: Callable[[str], str] = _default_normalize,
    warmup: int = 3,
    runs: int = 12,
) -> list[dict]:
    """Benchmark every command at every input point; return raw samples.

    Parallels ``core.run_suite`` but delegates the actual timing to hyperfine:

      * ``prepare(params)`` is called once per input point to materialize the
        fixture (e.g. generate a corpus file). Untimed setup, like ``Probe.prepare``.
      * A correctness gate runs each command once, normalizes stdout, and refuses
        to compare commands that disagree — so we never crown a fast-but-wrong
        command (claim C5 for the CLI regime).
      * hyperfine then times all commands at the point together, with warmup runs
        discarded, and exports JSON. We map its per-command ``times`` array into
        the shared raw-sample schema (claim C3).

    The returned list feeds ``stats.aggregate`` unchanged.
    """
    if shutil.which("hyperfine") is None:
        raise RuntimeError("hyperfine not found on PATH; install it to use this regime")

    samples: list[dict] = []

    for params in param_grid:
        if prepare is not None:
            prepare(params)

        # --- Correctness gate -------------------------------------------------
        # Run each command once for this input and compare normalized stdout.
        oracle: str | None = None
        oracle_name: str | None = None
        commands: list[str] = []
        for probe in probes:
            cmd = probe.command(params)
            commands.append(cmd)
            digest = _digest(normalize(_capture(cmd)))
            if oracle is None:
                oracle, oracle_name = digest, probe.name
            elif digest != oracle:
                raise ValueError(
                    f"CORRECTNESS GATE FAILED at params={params}: command "
                    f"{probe.name!r} produced normalized output {digest} but "
                    f"{oracle_name!r} produced {oracle}. Refusing to compare "
                    f"CLI commands that disagree on output."
                )

        # --- Measurement (delegated to hyperfine) -----------------------------
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="r"
        ) as tmp:
            json_path = Path(tmp.name)
        try:
            argv = [
                "hyperfine",
                "--warmup",
                str(warmup),
                "--runs",
                str(runs),
                "--export-json",
                str(json_path),
                *commands,
            ]
            subprocess.run(argv, check=True, capture_output=True, text=True)
            report = json.loads(json_path.read_text())
        finally:
            json_path.unlink(missing_ok=True)

        # hyperfine preserves command order in its results array; pair by index.
        results = report["results"]
        if len(results) != len(probes):
            raise RuntimeError(
                f"hyperfine returned {len(results)} results for {len(probes)} "
                f"commands at params={params}"
            )
        for probe, result in zip(probes, results):
            for rep, t in enumerate(result["times"]):
                samples.append(
                    {
                        "probe": probe.name,
                        "params": params,
                        "rep": rep,
                        "batch": 1,
                        "seconds_per_op": t,
                    }
                )

    return samples
