#!/usr/bin/env python3
"""Health-check monitor for ORCA optimization jobs.

Logic:
- Parse ORCA JSON every 10 minutes.
- If max gradient is not decreasing, kill process.
- Jitter geometry by +/−0.05 Å and restart.
- Stop once |dE| < 1e-6 Eh and RMS gradient < 1e-4.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class ConvergenceState:
    energy_change: float
    rms_gradient: float
    max_gradient: float


def parse_latest_state(json_path: Path) -> ConvergenceState | None:
    if not json_path.exists() or json_path.stat().st_size == 0:
        return None

    payload = json.loads(json_path.read_text())
    optimization = payload.get("optimization") or payload.get("Optimization") or {}
    steps = optimization.get("steps", [])
    if not steps:
        return None

    last = steps[-1]
    return ConvergenceState(
        energy_change=float(last.get("energy_change", 1.0)),
        rms_gradient=float(last.get("rms_gradient", 1.0)),
        max_gradient=float(last.get("max_gradient", 1.0)),
    )


def jitter_xyz(xyz_path: Path, out_path: Path, amplitude: float = 0.05) -> None:
    lines = xyz_path.read_text().splitlines()
    if len(lines) < 3:
        raise ValueError(f"Malformed XYZ file: {xyz_path}")

    natoms = int(lines[0].strip())
    header = lines[:2]
    geom = lines[2 : 2 + natoms]

    jittered = []
    for atom_line in geom:
        atom, x, y, z = atom_line.split()[:4]
        xj = float(x) + random.uniform(-amplitude, amplitude)
        yj = float(y) + random.uniform(-amplitude, amplitude)
        zj = float(z) + random.uniform(-amplitude, amplitude)
        jittered.append(f"{atom:2s} {xj: .8f} {yj: .8f} {zj: .8f}")

    out_path.write_text("\n".join([*header, *jittered]) + "\n")


def terminate_process_tree(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def launch_orca(orca_bin: str, input_file: Path, output_file: Path) -> subprocess.Popen:
    with output_file.open("w") as out:
        proc = subprocess.Popen([orca_bin, str(input_file)], stdout=out, stderr=subprocess.STDOUT)
    return proc


def should_stop(state: ConvergenceState, de_thresh: float, rms_thresh: float) -> bool:
    return abs(state.energy_change) < de_thresh and state.rms_gradient < rms_thresh


def monitor(
    workdir: Path,
    base_input: Path,
    json_output: Path,
    xyz_seed: Path,
    poll_seconds: int,
    orca_bin: str,
) -> int:
    attempt = 0
    previous_max_gradient = None
    proc = None

    while True:
        attempt += 1
        input_file = workdir / f"run_{attempt:03d}.inp"
        output_file = workdir / f"run_{attempt:03d}.out"
        local_xyz = workdir / f"jitter_{attempt:03d}.xyz"

        if attempt == 1:
            local_xyz.write_text(xyz_seed.read_text())
        else:
            jitter_xyz(workdir / f"jitter_{attempt-1:03d}.xyz", local_xyz)

        content = base_input.read_text().replace("{{XYZ_FILE}}", str(local_xyz))
        input_file.write_text(content)

        proc = launch_orca(orca_bin=orca_bin, input_file=input_file, output_file=output_file)
        print(f"[monitor] Started ORCA attempt {attempt} with PID {proc.pid}")

        while proc.poll() is None:
            time.sleep(poll_seconds)
            state = parse_latest_state(json_output)
            if state is None:
                print("[monitor] JSON unavailable yet, waiting...")
                continue

            print(
                f"[monitor] dE={state.energy_change:.3e} Eh | "
                f"RMS Grad={state.rms_gradient:.3e} | Max Grad={state.max_gradient:.3e}"
            )

            if should_stop(state, de_thresh=1e-6, rms_thresh=1e-4):
                print("[monitor] Convergence criteria met. Finishing job.")
                return 0

            if previous_max_gradient is not None and state.max_gradient >= previous_max_gradient:
                print("[monitor] Max gradient not decreasing; terminating and restarting with jitter.")
                terminate_process_tree(proc.pid)
                proc.wait(timeout=30)
                break

            previous_max_gradient = state.max_gradient

        if proc.returncode == 0:
            state = parse_latest_state(json_output)
            if state and should_stop(state, de_thresh=1e-6, rms_thresh=1e-4):
                return 0



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ORCA health-check monitor")
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--base-input", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--xyz-seed", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=int, default=600, help="10 minutes = 600 seconds")
    parser.add_argument("--orca-bin", default="orca")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return monitor(
        workdir=args.workdir,
        base_input=args.base_input,
        json_output=args.json_output,
        xyz_seed=args.xyz_seed,
        poll_seconds=args.poll_seconds,
        orca_bin=args.orca_bin,
    )


if __name__ == "__main__":
    raise SystemExit(main())
