#!/usr/bin/env bash
set -euo pipefail

ORCA_VERSION="6.0.0"
ORCA_ARCHIVE_NAME="orca_6_0_0_linux_x86-64_shared_openmpi411.tar.xz"
ORCA_URL="${ORCA_URL:-}"
ORCA_LOCAL_ARCHIVE="${ORCA_LOCAL_ARCHIVE:-/content/drive/MyDrive/DFT_Automation/assets/${ORCA_ARCHIVE_NAME}}"
ORCA_HOME="/content/orca_${ORCA_VERSION}"
PROJECT_ROOT="/content/drive/MyDrive/DFT_Automation"

ensure_orca_archive() {
  mkdir -p /content/downloads
  mkdir -p "$(dirname "${ORCA_LOCAL_ARCHIVE}")"

  if [[ -f "${ORCA_LOCAL_ARCHIVE}" ]]; then
    echo "[setup] Using local ORCA archive: ${ORCA_LOCAL_ARCHIVE}"
    cp "${ORCA_LOCAL_ARCHIVE}" "/content/downloads/${ORCA_ARCHIVE_NAME}"
    return
  fi

  if [[ -n "${ORCA_URL}" ]]; then
    echo "[setup] Downloading ORCA archive from: ${ORCA_URL}"
    wget --content-disposition -O "/content/downloads/${ORCA_ARCHIVE_NAME}" "${ORCA_URL}"
    if tar -tf "/content/downloads/${ORCA_ARCHIVE_NAME}" >/dev/null 2>&1; then
      return
    fi
    echo "[error] URL provided via ORCA_URL did not return a valid tar.xz archive."
  fi

  echo "[error] ORCA archive not found."
  echo "[hint] Upload licensed ORCA tarball to: ${ORCA_LOCAL_ARCHIVE}"
  echo "[hint] Or set ORCA_URL to a direct archive URL (not the forum detail page)."
  exit 2
}

echo "[setup] apt dependencies"
apt-get update -y
apt-get install -y wget tar xz-utils openmpi-bin libopenmpi-dev python3-pip file

if [[ ! -d "${ORCA_HOME}" ]]; then
  ensure_orca_archive
  cd /content
  tar -xJf "/content/downloads/${ORCA_ARCHIVE_NAME}"
  ORCA_SRC_DIR=$(find /content -maxdepth 1 -type d -name 'orca_*_shared_openmpi*' | head -n 1)
  if [[ -z "${ORCA_SRC_DIR}" ]]; then
    echo "[error] Could not locate extracted ORCA directory."
    exit 3
  fi
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
(root / 'assets').mkdir(parents=True, exist_ok=True)
for i in range(1, 11):
    (root / f'Job_{i:02d}').mkdir(parents=True, exist_ok=True)
print('Prepared Drive root/assets and 10 job folders.')
PY

echo "[setup] Done. ORCA at ${ORCA_HOME}"
