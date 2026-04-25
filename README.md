# DFT-Battery-Automation

Automation scaffold for studying fluorinated amide additives in aqueous Li-ion batteries using ORCA 6.1.1 and OPI.

## Layout

- `.github/workflows/colab_dispatch.yml`: creates 10 unique job manifests and parallel status matrix.
- `src/install_orca.sh`: Colab setup for ORCA + OPI and Drive job folders.
- `src/monitor.py`: health-check restart logic (10 min polling, gradient trend checks, geometry jitter).
- `src/analysis_XAI.py`: binding energy/HOMO-LUMO analysis + manuscript artifact generation.
- `notebooks/Main_Pipeline.ipynb`: one-click Colab orchestration notebook.
- `inputs/`: seed XYZ geometries.
- `templates/`: ORCA input and manuscript templates.

## Safety for 10-unit execution
Always use unique Drive subfolders (`Job_01 ... Job_10`) and separate Colab sessions/accounts to avoid file locking.
