# DFT-Battery-Automation

Colab-first automation for **Synergistic Fluorinated Amide Additives for Aqueous Li-ion Batteries**.

## One-cell Colab launcher

> Before running: upload your licensed ORCA tarball to
> `/content/drive/MyDrive/DFT_Automation/assets/orca_6_0_0_linux_x86-64_shared_openmpi411.tar.xz`

```python
from google.colab import drive

drive.mount('/content/drive', force_remount=True)
!git clone https://github.com/abdulkareem/DFT-BatteryAutomation.git
%cd DFT-BatteryAutomation
!python src/colab_one_cell_runner.py --run-jobs --analyze
```

## Why previous run failed
ORCA forum download links can return an HTML page when authentication is required. The installer now validates the archive and prints a clear hint to use a locally provided tarball in Drive.

## Highlights
- ORCA 6.0 installation and environment setup for Colab.
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
