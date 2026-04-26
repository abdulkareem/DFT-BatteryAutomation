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

## Using a Google Drive share link directly
If you have a share link like:
`https://drive.google.com/file/d/<FILE_ID>/view?usp=drive_link`

run in Colab:

```python
import os
os.environ['ORCA_GDRIVE_LINK'] = 'https://drive.google.com/file/d/1ff8ky4lNust0m0N0f3EvYd_Tw9Hmx9K2/view?usp=drive_link'
!python src/colab_one_cell_runner.py --run-jobs --analyze
```

(If you prefer shell syntax in Colab, use `%%bash` or `%env`, not plain `export` in a Python cell.)

The installer will try `gdown` download automatically from `ORCA_GDRIVE_LINK` if local assets are missing.

## Mounting a specific Google account and saving all outputs
Colab cannot be forced by script to authenticate a specific Google account. You must sign in manually during `drive.mount(...)` and choose the account (e.g., `abdulkareem@psmocollege.ac.in`).

To force all pipeline outputs into that mounted Drive folder:

```python
import os
os.environ['DFT_PROJECT_ROOT'] = '/content/drive/MyDrive/DFT_Automation'
!python src/colab_one_cell_runner.py --run-jobs --analyze
```

All jobs, manifests, analysis CSV/plots, and manuscript outputs are written under `$DFT_PROJECT_ROOT`.

## Troubleshooting: `can't open file ... src/colab_one_cell_runner.py`
This means your current path is not the repository that contains the runner.

Use this in Colab:

```bash
%cd /content
!find /content -maxdepth 3 -type f -path '*/src/colab_one_cell_runner.py'
```

Then `cd` into that repo root and run:

```bash
%cd /content/DFT-BatteryAutomation
!python src/colab_one_cell_runner.py --run-jobs --analyze
```

If your repo folder is named differently (for example `/content/ensemble_higherversion`), make sure it actually contains `src/colab_one_cell_runner.py`.

## Running on Kaggle (yes, with small changes)
This pipeline can run on Kaggle, but do **not** use Colab-specific `google.colab` mounting code.

Use Kaggle working storage instead:

```python
import os
os.environ['DFT_PROJECT_ROOT'] = '/kaggle/working/DFT_Automation'
# Optional: provide ORCA link if not manually uploaded
# os.environ['ORCA_GDRIVE_LINK'] = '<your-shared-drive-link>'
!python src/colab_one_cell_runner.py --run-jobs --analyze
```

Notes:
- Kaggle has no Google Drive mount like `/content/drive`; use `/kaggle/working`.
- For real ORCA runs, upload installer/archive into `$DFT_PROJECT_ROOT/assets` first.
- If ORCA binary is unavailable, mock mode still allows full workflow validation.
