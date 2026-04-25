#!/usr/bin/env python3
"""One-shot Colab runner for DFT_Automation workflow.

Usage in Colab (single cell):
  !python src/colab_one_cell_runner.py --run-jobs --analyze
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/content/drive/MyDrive/DFT_Automation")
REPO_ROOT = Path(__file__).resolve().parents[1]
ORCA_HOME = Path("/content/orca_6.1.1")


class PipelineError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("[cmd]", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)
    except subprocess.CalledProcessError as exc:
        raise PipelineError(f"Command failed ({exc.returncode}): {' '.join(cmd)}") from exc


def prepare_environment() -> None:
    orca_bin = ORCA_HOME / "orca"
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


def _mock_mode() -> bool:
    return (ORCA_HOME / ".mock_mode").exists()


def _orca_exec() -> str:
    exe = ORCA_HOME / "orca"
    if exe.exists():
        return str(exe)
    return "orca"


def generate_mock_results(max_jobs: int = 10) -> None:
    manifest = json.loads((PROJECT_ROOT / "job_manifest.json").read_text())
    for i, entry in enumerate(manifest[:max_jobs], start=1):
        job_dir = PROJECT_ROOT / entry["job_id"]
        base = -100.0 - i * 0.05
        payload = {
            "job_id": entry["job_id"],
            "system": entry["system"],
            "energies": {
                "E_complex": base,
                "E_Li_plus": -7.20,
                "E_fragments": base + 0.10,
            },
            "orbitals": {
                "HOMO_eV": -6.2 + random.uniform(-0.2, 0.2),
                "LUMO_eV": -0.8 + random.uniform(-0.2, 0.2),
            },
            "xai": {
                "IBO_Li_O": 0.45 + random.uniform(-0.05, 0.05),
                "ESP_F_shield": 0.65 + random.uniform(-0.05, 0.05),
            },
        }
        (job_dir / "result.json").write_text(json.dumps(payload, indent=2))


def run_jobs(max_jobs: int = 10) -> None:
    manifest = json.loads((PROJECT_ROOT / "job_manifest.json").read_text())
    orca_exec = _orca_exec()
    for entry in manifest[:max_jobs]:
        job_dir = PROJECT_ROOT / entry["job_id"]
        print(f"\n=== {entry['job_id']} ({entry['system']}) ===")
        run([orca_exec, str(job_dir / "preopt_xtb.inp")], cwd=job_dir)
        run([orca_exec, str(job_dir / "job.inp")], cwd=job_dir)

    if _mock_mode():
        print("[mock] Generating synthetic result.json files for analysis.")
        generate_mock_results(max_jobs=max_jobs)


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

    try:
        prepare_environment()
        stage_xyz()

        if args.run_jobs:
            run_jobs(max_jobs=args.max_jobs)

        if args.analyze:
            analyze()

        print("[done] Pipeline completed.")
        return 0
    except PipelineError as exc:
        print("\n[failed] Pipeline aborted.")
        print(f"[reason] {exc}")
        print(
            "[next-step] For real DFT runs, place ORCA package in "
            "/content/drive/MyDrive/DFT_Automation/assets/ (run or tar.xz)"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
