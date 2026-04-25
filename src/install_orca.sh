#!/usr/bin/env bash
set -euo pipefail

ORCA_VERSION="6.1.1"
ORCA_DIST="orca_6_1_1_linux_x86-64_shared_openmpi416.tar.xz"
ORCA_URL="https://orcaforum.kofo.mpg.de/app.php/dlext/?view=detail&df_id=208"
ORCA_HOME="/content/orca_${ORCA_VERSION}"
PROJECT_ROOT="/content/drive/My Drive/DFT_Project"

echo "[install_orca] Installing OS dependencies..."
apt-get update -y
apt-get install -y wget tar xz-utils openmpi-bin libopenmpi-dev python3-pip

if [[ ! -d "${ORCA_HOME}" ]]; then
  echo "[install_orca] Downloading ORCA ${ORCA_VERSION}..."
  wget -O /content/${ORCA_DIST} "${ORCA_URL}"
  mkdir -p "${ORCA_HOME}"
  tar -xJf /content/${ORCA_DIST} -C /content
  mv /content/orca_*_shared_openmpi416/* "${ORCA_HOME}" || true
fi

echo "[install_orca] Installing Python dependencies (OPI + analysis stack)..."
python3 -m pip install --upgrade pip
python3 -m pip install \
  orca-python-interface \
  numpy pandas matplotlib pydantic scipy python-docx reportlab jinja2 pyyaml

cat <<BASHRC >/etc/profile.d/orca.sh
export ORCA_HOME=${ORCA_HOME}
export PATH=${ORCA_HOME}:\$PATH
export LD_LIBRARY_PATH=${ORCA_HOME}:\$LD_LIBRARY_PATH
BASHRC

export ORCA_HOME="${ORCA_HOME}"
export PATH="${ORCA_HOME}:${PATH}"
export LD_LIBRARY_PATH="${ORCA_HOME}:${LD_LIBRARY_PATH:-}"

python3 - <<'PY'
from pathlib import Path

root = Path('/content/drive/My Drive/DFT_Project')
root.mkdir(parents=True, exist_ok=True)
for idx in range(1, 11):
    (root / f'Job_{idx:02d}').mkdir(parents=True, exist_ok=True)
print('[install_orca] Created persistent job folders in Google Drive.')
PY

echo "[install_orca] Completed. ORCA path: ${ORCA_HOME}"
