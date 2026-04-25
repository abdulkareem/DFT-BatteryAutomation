#!/usr/bin/env python3
"""Post-processing for binding energies, HOMO-LUMO gaps, XAI descriptors, and manuscript draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HARTREE_TO_KJMOL = 2625.5


def parse_result(result_json: Path) -> dict:
    raw = json.loads(result_json.read_text())
    energies = raw.get("energies", {})
    orbitals = raw.get("orbitals", {})
    xai = raw.get("xai", {})
    return {
        "job_id": raw.get("job_id", result_json.parent.name),
        "system": raw.get("system", "unknown"),
        "E_complex": float(energies.get("E_complex", 0.0)),
        "E_Li": float(energies.get("E_Li_plus", 0.0)),
        "E_fragments": float(energies.get("E_fragments", 0.0)),
        "HOMO_eV": float(orbitals.get("HOMO_eV", 0.0)),
        "LUMO_eV": float(orbitals.get("LUMO_eV", 0.0)),
        "IBO_Li_O": float(xai.get("IBO_Li_O", 0.0)),
        "ESP_F_shield": float(xai.get("ESP_F_shield", 0.0)),
    }


def compute(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["delta_Eb_Eh"] = df["E_complex"] - (df["E_Li"] + df["E_fragments"])
    df["delta_Eb_kJmol"] = df["delta_Eb_Eh"] * HARTREE_TO_KJMOL
    df["gap_eV"] = df["LUMO_eV"] - df["HOMO_eV"]
    return df


def plot_binding(df: pd.DataFrame, out_png: Path) -> None:
    grouped = df.groupby("system", as_index=False)["delta_Eb_kJmol"].mean().sort_values("delta_Eb_kJmol")
    plt.figure(figsize=(9, 4.8))
    plt.bar(grouped["system"], grouped["delta_Eb_kJmol"], color="#2a7fb8")
    plt.ylabel("Binding Energy ΔEb (kJ/mol)")
    plt.xlabel("Solvation Shell Composition")
    plt.title("Binding Energy vs. Solvation Shell Composition")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(out_png, dpi=220)
    plt.close()


def write_manuscript(df: pd.DataFrame, out_md: Path) -> None:
    means = df.groupby("system", as_index=False)[["delta_Eb_kJmol", "gap_eV", "IBO_Li_O", "ESP_F_shield"]].mean()
    synergy = means[means["system"].str.contains("TFA\)1\(NDT", regex=True, na=False)]
    synergy_text = "Synergistic case not found in dataset."
    if not synergy.empty:
        row = synergy.iloc[0]
        synergy_text = (
            f"The dual-amide shell shows ΔEb={row['delta_Eb_kJmol']:.2f} kJ/mol, "
            f"gap={row['gap_eV']:.2f} eV, IBO(Li-O)={row['IBO_Li_O']:.3f}, "
            f"and ESP fluorine-shield index={row['ESP_F_shield']:.3f}."
        )

    text = f"""# Draft Manuscript

## Methods
We used ORCA 6.0 with `! PBEh-3c Opt RIJONX CPCM(Water)` for production optimizations. PBEh-3c was selected because it is computationally efficient for non-covalent coordination environments while retaining robust geometric and energetic trends for solvated Li+ clusters. A two-stage acceleration protocol was used: a short XTB pre-optimization followed by final PBEh-3c optimization.

## Results
Binding energies and HOMO-LUMO gaps were extracted into `summary.csv`. The synergistic dual-amide system was benchmarked against control and single-additive shells.

{synergy_text}

XAI descriptors were included: IBO metrics to quantify Li-O electron sharing and ESP shield indices to quantify fluorine-driven electrostatic exclusion of water.
"""
    out_md.write_text(text)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()

    rows = []
    for path in sorted(args.jobs_root.glob("Job_*/result.json")):
        rows.append(parse_result(path))
    if not rows:
        raise FileNotFoundError("No Job_*/result.json files discovered")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = compute(pd.DataFrame(rows))
    summary_csv = args.output_dir / "summary.csv"
    df.to_csv(summary_csv, index=False)
    plot_binding(df, args.output_dir / "binding_vs_solvation_shell.png")
    write_manuscript(df, args.output_dir / "manuscript.md")
    print(f"Saved {summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
