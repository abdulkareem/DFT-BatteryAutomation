#!/usr/bin/env python3
"""Smart monitor for ORCA output.

- Poll every 500 s.
- Exit success when MAX GRADIENT < 1e-4.
- If SCF energy unchanged for 20 cycles, stop job, rotate NDT by 2 degrees, restart from .gbw.
"""

from __future__ import annotations

import argparse
import math
import random
import re
import signal
import subprocess
import time
from pathlib import Path

ENERGY_RE = re.compile(r"Total Energy\s*:\s*(-?\d+\.\d+)")
MAX_GRAD_RE = re.compile(r"MAX\s+GRADIENT\s+([-+]?\d+\.\d+(?:[Ee][-+]?\d+)?)")


def parse_out(out_file: Path) -> tuple[list[float], float | None]:
    energies: list[float] = []
    max_grad = None
    if not out_file.exists():
        return energies, max_grad

    for line in out_file.read_text(errors="ignore").splitlines():
        em = ENERGY_RE.search(line)
        if em:
            energies.append(float(em.group(1)))
        gm = MAX_GRAD_RE.search(line)
        if gm:
            max_grad = float(gm.group(1))
    return energies, max_grad


def energy_flat_for_20_cycles(energies: list[float], tol: float = 1e-9) -> bool:
    if len(energies) < 20:
        return False
    window = energies[-20:]
    return max(window) - min(window) < tol


def rotate_points(coords: list[tuple[str, float, float, float]], theta_deg: float) -> list[tuple[str, float, float, float]]:
    theta = math.radians(theta_deg)
    c, s = math.cos(theta), math.sin(theta)
    out = []
    for el, x, y, z in coords:
        xr = c * x - s * y
        yr = s * x + c * y
        out.append((el, xr, yr, z))
    return out


def read_xyz(path: Path) -> tuple[int, str, list[tuple[str, float, float, float]]]:
    lines = path.read_text().splitlines()
    n = int(lines[0])
    comment = lines[1] if len(lines) > 1 else ""
    atoms = []
    for ln in lines[2 : 2 + n]:
        el, x, y, z = ln.split()[:4]
        atoms.append((el, float(x), float(y), float(z)))
    return n, comment, atoms


def write_xyz(path: Path, n: int, comment: str, atoms: list[tuple[str, float, float, float]]) -> None:
    body = [f"{el} {x:.8f} {y:.8f} {z:.8f}" for el, x, y, z in atoms]
    path.write_text(f"{n}\n{comment}\n" + "\n".join(body) + "\n")


def rotate_ndt_ligand(xyz_path: Path, theta: float = 2.0) -> None:
    n, comment, atoms = read_xyz(xyz_path)
    # heuristic: rotate heavy atoms beyond first 5 atoms (assumed NDT fragment region)
    head = atoms[:5]
    tail = atoms[5:]
    if not tail:
        tail = atoms
        head = []
    rotated_tail = rotate_points(tail, theta_deg=random.choice([-theta, theta]))
    write_xyz(xyz_path, n, comment + " | rotated NDT fragment", head + rotated_tail)


def start_orca(input_file: Path, out_file: Path, gbw: Path | None = None) -> subprocess.Popen:
    cmd = ["orca", str(input_file)]
    if gbw and gbw.exists():
        cmd.extend(["--gbw", str(gbw)])
    out_handle = out_file.open("a")
    return subprocess.Popen(cmd, stdout=out_handle, stderr=subprocess.STDOUT)


def run_monitor(workdir: Path, xyz_file: Path, poll: int = 500) -> int:
    inp = workdir / "job.inp"
    out = workdir / "job.out"
    gbw = workdir / "job.gbw"

    proc = start_orca(inp, out)
    print(f"Started ORCA PID={proc.pid}")

    while True:
        time.sleep(poll)
        energies, max_grad = parse_out(out)

        if max_grad is not None:
            print(f"MAX GRADIENT = {max_grad:.3e}")
            if max_grad < 1e-4:
                proc.send_signal(signal.SIGTERM)
                print("Converged threshold reached. Stopping and saving.")
                return 0

        if energy_flat_for_20_cycles(energies):
            print("Energy plateau for 20 SCF cycles. Restarting with 2-degree NDT rotation.")
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=60)
            rotate_ndt_ligand(xyz_file, theta=2.0)
            proc = start_orca(inp, out, gbw=gbw)

        if proc.poll() is not None and proc.returncode != 0:
            print(f"ORCA exited with code {proc.returncode}. Restarting.")
            proc = start_orca(inp, out, gbw=gbw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--xyz-file", type=Path, required=True)
    ap.add_argument("--poll-seconds", type=int, default=500)
    args = ap.parse_args()
    return run_monitor(args.workdir, args.xyz_file, args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
