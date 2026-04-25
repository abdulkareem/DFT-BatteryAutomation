#!/usr/bin/env python3
"""Verify ORCA installer/archive size and signature in Colab Drive."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_head(path: Path, n_mb: int = 16) -> str:
    h = hashlib.sha256()
    chunk = 1024 * 1024
    remaining = n_mb * chunk
    with path.open("rb") as f:
        while remaining > 0:
            b = f.read(min(chunk, remaining))
            if not b:
                break
            h.update(b)
            remaining -= len(b)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--assets", default="/content/drive/MyDrive/DFT_Automation/assets")
    args = p.parse_args()

    assets = Path(args.assets)
    files = list(assets.glob("orca*_linux*x86-64*shared*"))
    if not files:
        print(f"No ORCA candidates found in {assets}")
        return 1

    for f in sorted(files):
        size_mb = f.stat().st_size / (1024 * 1024)
        with f.open("rb") as fh:
            sig = fh.read(4)
        print(f"{f.name}: {size_mb:.1f} MB")
        print(f"  first4 bytes: {sig!r}")
        print(f"  sha256(first16MB): {sha256_head(f)}")
        if size_mb < 50:
            print("  [WARN] file is unexpectedly small; likely incomplete upload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
