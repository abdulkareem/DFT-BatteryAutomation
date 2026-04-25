# DFT-Battery-Automation

Colab-first automation for **Synergistic Fluorinated Amide Additives for Aqueous Li-ion Batteries**.

## One-cell Colab launcher (supports ORCA 6.1.1 installer version)

```python
from google.colab import drive

drive.mount('/content/drive', force_remount=True)
%cd /content
!rm -rf DFT-BatteryAutomation
!git clone https://github.com/abdulkareem/DFT-BatteryAutomation.git
%cd /content/DFT-BatteryAutomation
!python src/colab_one_cell_runner.py --run-jobs --analyze
```

### ORCA 6.1.1 package placement
Put **either** of these into:
`/content/drive/MyDrive/DFT_Automation/assets/`

- `orca_6_1_1_linux_x86-64_shared_openmpi416.run`  ← installer version
- `orca_6_1_1_linux_x86-64_shared_openmpi416.tar.xz`  ← archive version

If neither is present, the pipeline falls back to mock mode for workflow testing.

## Highlights
- ORCA 6.1.1 installation (archive or installer) with mock fallback.
- Google Drive persistence at `/content/drive/MyDrive/DFT_Automation/`.
- 10 parallel job folders (`Job_01` ... `Job_10`) with input factory for:
  - `Li+(H2O)4` (control)
  - `Li+(TFA)1(H2O)3`
  - `Li+(NDT)1(H2O)3`
  - `Li+(TFA)1(NDT)1(H2O)2` (synergistic)
- Two-stage compute strategy: XTB pre-opt then `! PBEh-3c Opt RIJONX CPCM(Water)`.
- Smart monitor: checks `.out` every 500 s, converges on `MAX GRADIENT < 1e-4`, restarts on 20-cycle energy plateaus with 2° NDT rotation and `.gbw` restart.
- Analysis for `summary.csv`, binding-energy plot, and `manuscript.md` with methods/results draft.
- XAI descriptors supported in result schema: IBO Li-O metric and ESP fluorine-shield index.


If you still see old `orca_6_0_0...` hints, run `!git pull` in Colab to get the latest installer script.


If installer is detected but cannot be unpacked, setup now fails fast and prints `/tmp/orca_installer.log` tail instead of silently switching to mock mode.


If you see `Unexpected archive size`, re-upload the `.run` file (it is likely truncated). The installer now performs `--check` and a minimum size validation before install.


Quick check in Colab:
`!ls -lh /content/drive/MyDrive/DFT_Automation/assets`
If the ORCA `.run` is only a few MB (e.g., 8 MB), it is incomplete; re-upload the full file.

## If a 450 MB upload shows as 8 MB in Drive
Use this reliable Colab upload flow (uploads to VM first, then copies to Drive):

```python
from google.colab import files
from pathlib import Path

assets = Path('/content/drive/MyDrive/DFT_Automation/assets')
assets.mkdir(parents=True, exist_ok=True)

uploaded = files.upload()  # pick your ORCA .run/.tar.xz from local machine
name, payload = next(iter(uploaded.items()))
name = Path(name).name
out = assets / name
out.write_bytes(payload)
print('Saved:', out, 'size=', out.stat().st_size)
```

Then verify in Colab:

```bash
!python src/verify_orca_asset.py
!ls -lh /content/drive/MyDrive/DFT_Automation/assets
```

If size is still far below expected (e.g., 8 MB), the upload was interrupted or browser-limited; re-upload from a stable connection and avoid closing the tab.

## Important: `conda install orca` is **not** ORCA quantum chemistry
In conda-forge, `orca` typically refers to a different package name collision (not the licensed ORCA QC binary from the ORCA forum/official distribution).

For this project, use one of these:
1. Place your licensed ORCA installer/archive in Drive assets and run the provided installer script.
2. Use mock mode for pipeline testing if licensed binaries are unavailable.

Do **not** rely on `conda install -c conda-forge orca` for ORCA QC production calculations.
