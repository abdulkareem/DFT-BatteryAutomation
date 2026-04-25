#!/usr/bin/env bash
set -euo pipefail

ORCA_VERSION="6.0.0"
ORCA_ARCHIVE="orca_6_0_0_linux_x86-64_shared_openmpi411.tar.xz"
ORCA_URL="https://orcaforum.kofo.mpg.de/app.php/dlext/?view=detail&df_id=180"
ORCA_HOME="/content/orca_${ORCA_VERSION}"
PROJECT_ROOT="/content/drive/MyDrive/DFT_Automation"

echo "[setup] apt dependencies"
apt-get update -y
apt-get install -y wget tar xz-utils openmpi-bin libopenmpi-dev python3-pip

if [[ ! -d "${ORCA_HOME}" ]]; then
  cd /content
  wget -O "${ORCA_ARCHIVE}" "${ORCA_URL}"
  tar -xJf "${ORCA_ARCHIVE}"
  ORCA_SRC_DIR=$(find /content -maxdepth 1 -type d -name 'orca_*_shared_openmpi*' | head -n 1)
  mkdir -p "${ORCA_HOME}"
  cp -r "${ORCA_SRC_DIR}"/* "${ORCA_HOME}"/
fi

python3 -m pip install --upgrade pip
python3 -m pip install numpy pandas matplotlib scipy mendeleev pyyaml

cat <<ENV >/etc/profile.d/orca.sh
export ORCA_HOME=${ORCA_HOME}
export PATH=${ORCA_HOME}:\$PATH
export LD_LIBRARY_PATH=${ORCA_HOME}:\$LD_LIBRARY_PATH
ENV

python3 - <<'PY'
from pathlib import Path
root = Path('/content/drive/MyDrive/DFT_Automation')
root.mkdir(parents=True, exist_ok=True)
for i in range(1, 11):
    (root / f'Job_{i:02d}').mkdir(parents=True, exist_ok=True)
print('Prepared Drive root and 10 job folders.')
PY

echo "[setup] Done. ORCA at ${ORCA_HOME}"
