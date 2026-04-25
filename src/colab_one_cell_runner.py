#!/usr/bin/env python3
"""One-shot Colab runner for DFT_Automation workflow.

Usage in Colab (single cell):
  !python src/colab_one_cell_runner.py --run-jobs --analyze
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/content/drive/MyDrive/DFT_Automation")
REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("[cmd]", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def prepare_environment() -> None:
    orca_bin = Path("/content/orca_6.0.0/orca")
    if not orca_bin.exists():
        run(["bash", str(REPO_ROOT / "src" / "install_orca.sh")])
    else:
        print("[setup] Existing ORCA installation detected; skipping installer.")
    run(["python", str(REPO_ROOT / "src" / "job_factory.py")])


def stage_xyz() -> None:
    for job_dir in sorted(PROJECT_ROOT.glob("Job_*")):
        for name in ["control.xyz", "tfa.xyz", "ndt.xyz", "synergy.xyz"]:
            src = REPO_ROOT / "inputs" / name
            if src.exists():
                shutil.copy(src, job_dir / name)
    print("[stage] Seed XYZ files copied into all job folders.")


def run_jobs(max_jobs: int = 10) -> None:
    manifest = json.loads((PROJECT_ROOT / "job_manifest.json").read_text())
    for entry in manifest[:max_jobs]:
        job_dir = PROJECT_ROOT / entry["job_id"]
        print(f"\n=== {entry['job_id']} ({entry['system']}) ===")
        run(["orca", str(job_dir / "preopt_xtb.inp")], cwd=job_dir)
        run(["orca", str(job_dir / "job.inp")], cwd=job_dir)


def analyze() -> None:
    out_dir = PROJECT_ROOT / "analysis"
    run(
        [
            "python",
            str(REPO_ROOT / "src" / "analysis_XAI.py"),
            "--jobs-root",
            str(PROJECT_ROOT),
            "--output-dir",
            str(out_dir),
        ]
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-jobs", action="store_true", help="Run all jobs after setup")
    p.add_argument("--analyze", action="store_true", help="Run post-processing at the end")
    p.add_argument("--max-jobs", type=int, default=10)
    args = p.parse_args()

    prepare_environment()
    stage_xyz()

    if args.run_jobs:
        run_jobs(max_jobs=args.max_jobs)

    if args.analyze:
        analyze()

    print("[done] Pipeline completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
