#!/usr/bin/env python3
"""Generate 10 job folders and ORCA inputs for control/additive/synergistic cases."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

SYSTEMS = {
    "control": "Li+(H2O)4",
    "tfa": "Li+(TFA)1(H2O)3",
    "ndt": "Li+(NDT)1(H2O)3",
    "synergy": "Li+(TFA)1(NDT)1(H2O)2",
}


@dataclass
class JobConfig:
    job_id: str
    system_key: str


def assign_jobs() -> list[JobConfig]:
    keys = ["control", "tfa", "ndt", "synergy", "control", "tfa", "ndt", "synergy", "synergy", "synergy"]
    return [JobConfig(job_id=f"Job_{i+1:02d}", system_key=keys[i]) for i in range(10)]


def make_input(xyz_name: str, nprocs: int = 4) -> str:
    return f"""! PBEh-3c Opt RIJONX CPCM(Water)
%pal nprocs {nprocs} end
%maxcore 1800
%scf
  MaxIter 300
end
%elprop
  dipole true
end
%plots
  dim1 80
  dim2 80
  dim3 80
  Format Gaussian_Cube
end
%output
  Print[ P_OrbEn ] 1
  Print[ P_BondOrders_M ] 1
end
%ibo
  IBO true
end
* xyzfile 1 1 {xyz_name}
"""


def write_preopt(job_dir: Path, xyz_name: str) -> None:
    text = f"""! XTB Opt
%pal nprocs 2 end
* xyzfile 1 1 {xyz_name}
"""
    (job_dir / "preopt_xtb.inp").write_text(text)


def main(project_root: Path) -> None:
    manifest = []
    for cfg in assign_jobs():
        job_dir = project_root / cfg.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        xyz = f"{cfg.system_key}.xyz"
        (job_dir / "job.inp").write_text(make_input(xyz))
        write_preopt(job_dir, xyz)
        manifest.append(
            {
                "job_id": cfg.job_id,
                "system": SYSTEMS[cfg.system_key],
                "input": str((job_dir / "job.inp")),
                "gbw": str((job_dir / "job.gbw")),
            }
        )

    (project_root / "job_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(manifest)} jobs to {project_root}")


if __name__ == "__main__":
    root = Path(os.environ.get("DFT_PROJECT_ROOT", "/content/drive/MyDrive/DFT_Automation"))
    main(root)
