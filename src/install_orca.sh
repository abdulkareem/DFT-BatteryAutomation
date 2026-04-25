#!/usr/bin/env bash
set -euo pipefail

ORCA_VERSION="6.1.1"
ASSETS_DIR="/content/drive/MyDrive/DFT_Automation/assets"
ORCA_ARCHIVE_NAME_DEFAULT="orca_6_1_1_linux_x86-64_shared_openmpi416.tar.xz"
ORCA_INSTALLER_NAME_DEFAULT="orca_6_1_1_linux_x86-64_shared_openmpi416.run"
ORCA_URL="${ORCA_URL:-}"
ORCA_LOCAL_ARCHIVE="${ORCA_LOCAL_ARCHIVE:-${ASSETS_DIR}/${ORCA_ARCHIVE_NAME_DEFAULT}}"
ORCA_LOCAL_INSTALLER="${ORCA_LOCAL_INSTALLER:-${ASSETS_DIR}/${ORCA_INSTALLER_NAME_DEFAULT}}"
ORCA_HOME="/content/orca_${ORCA_VERSION}"
ALLOW_MOCK_ORCA="${ALLOW_MOCK_ORCA:-1}"
INSTALLER_LOG="/tmp/orca_installer.log"

resolve_asset_candidates() {
  mkdir -p "${ASSETS_DIR}"

  if [[ ! -f "${ORCA_LOCAL_ARCHIVE}" ]]; then
    local alt_archive
    alt_archive=$(find "${ASSETS_DIR}" -maxdepth 1 -type f -name 'orca*_linux*x86-64*shared*.tar.xz' | head -n 1 || true)
    [[ -n "${alt_archive}" ]] && ORCA_LOCAL_ARCHIVE="${alt_archive}"
  fi

  if [[ ! -f "${ORCA_LOCAL_INSTALLER}" ]]; then
    local alt_installer
    alt_installer=$(find "${ASSETS_DIR}" -maxdepth 1 -type f \( -name 'orca*_linux*x86-64*shared*.run' -o -name 'orca*_linux*x86-64*shared*.sh' \) | head -n 1 || true)
    [[ -n "${alt_installer}" ]] && ORCA_LOCAL_INSTALLER="${alt_installer}"
  fi
}

create_mock_orca() {
  echo "[setup] Creating mock ORCA executable (no licensed binary found)."
  mkdir -p "${ORCA_HOME}"
  cat > "${ORCA_HOME}/orca" <<'MOCK'
#!/usr/bin/env bash
set -euo pipefail
inp="${1:-job.inp}"
base="${inp%.*}"
echo "ORCA MOCK RUN for $inp"
echo "Total Energy       : -100.000000"
echo "MAX GRADIENT       9.9e-05"
touch "${base}.gbw"
MOCK
  chmod +x "${ORCA_HOME}/orca"
  touch "${ORCA_HOME}/.mock_mode"
}

copy_discovered_orca() {
  local candidate
  candidate=$(find /content -maxdepth 6 -type f -name orca | grep -v "/orca_${ORCA_VERSION}/orca" | head -n 1 || true)
  if [[ -n "$candidate" ]]; then
    mkdir -p "$ORCA_HOME"
    cp -r "$(dirname "$candidate")"/* "$ORCA_HOME"/
  fi
}


validate_installer() {
  local installer="$1"
  local size
  size=$(stat -c%s "$installer" 2>/dev/null || echo 0)
  if [[ "$size" -lt 50000000 ]]; then
    echo "[error] Installer appears too small (${size} bytes). Likely incomplete/corrupt upload."
    return 1
  fi

  set +e
  "$installer" --check >>"$INSTALLER_LOG" 2>&1
  local rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo "[error] Installer integrity check failed (--check)."
    return 1
  fi
  return 0
}

try_install_from_installer() {
  local installer="$1"
  chmod +x "$installer"
  : > "$INSTALLER_LOG"
  echo "[setup] Trying ORCA installer: $installer"

  validate_installer "$installer" || return 1

  set +e
  "$installer" --mode unattended --prefix "$ORCA_HOME" >>"$INSTALLER_LOG" 2>&1
  local rc1=$?
  "$installer" --target "$ORCA_HOME" >>"$INSTALLER_LOG" 2>&1
  local rc2=$?
  "$installer" --noexec --target /content/orca_unpack >>"$INSTALLER_LOG" 2>&1
  local rc3=$?
  bash "$installer" --noexec --target /content/orca_unpack2 >>"$INSTALLER_LOG" 2>&1
  local rc4=$?
  set -e

  [[ -x "$ORCA_HOME/orca" ]] || copy_discovered_orca

  if [[ -x "$ORCA_HOME/orca" ]]; then
    return 0
  fi

  echo "[warn] Installer attempts failed (codes: $rc1, $rc2, $rc3, $rc4)."
  return 1
}

install_from_archive() {
  local archive="$1"
  mkdir -p /content/downloads
  cp "$archive" /content/downloads/orca_pkg.tar.xz
  tar -xJf /content/downloads/orca_pkg.tar.xz -C /content
  local src_dir
  src_dir=$(find /content -maxdepth 2 -type d -name 'orca_*_shared_openmpi*' | head -n 1)
  [[ -n "$src_dir" ]] || return 1
  mkdir -p "$ORCA_HOME"
  cp -r "$src_dir"/* "$ORCA_HOME"/
  [[ -x "$ORCA_HOME/orca" ]]
}

echo "[setup] apt dependencies"
apt-get update -y
apt-get install -y wget tar xz-utils openmpi-bin libopenmpi-dev python3-pip file

resolve_asset_candidates

echo "[setup] Asset archive candidate: ${ORCA_LOCAL_ARCHIVE}"
echo "[setup] Asset installer candidate: ${ORCA_LOCAL_INSTALLER}"

had_user_package=0
if [[ -f "${ORCA_LOCAL_ARCHIVE}" || -f "${ORCA_LOCAL_INSTALLER}" || -n "${ORCA_URL}" ]]; then
  had_user_package=1
fi

if [[ ! -x "${ORCA_HOME}/orca" ]]; then
  if [[ -f "${ORCA_LOCAL_ARCHIVE}" ]]; then
    echo "[setup] Using local ORCA archive"
    install_from_archive "${ORCA_LOCAL_ARCHIVE}" || true
  fi

  if [[ ! -x "${ORCA_HOME}/orca" && -f "${ORCA_LOCAL_INSTALLER}" ]]; then
    echo "[setup] Using local ORCA installer"
    try_install_from_installer "${ORCA_LOCAL_INSTALLER}" || true
  fi

  if [[ ! -x "${ORCA_HOME}/orca" && -n "${ORCA_URL}" ]]; then
    echo "[setup] Downloading ORCA package from ORCA_URL"
    wget --content-disposition -O /content/downloads/orca_pkg "${ORCA_URL}" || true
    if file /content/downloads/orca_pkg | grep -qi 'XZ compressed'; then
      mv /content/downloads/orca_pkg /content/downloads/orca_pkg.tar.xz
      install_from_archive /content/downloads/orca_pkg.tar.xz || true
    else
      chmod +x /content/downloads/orca_pkg || true
      try_install_from_installer /content/downloads/orca_pkg || true
    fi
  fi

  if [[ ! -x "${ORCA_HOME}/orca" ]]; then
    if [[ "$had_user_package" == "1" ]]; then
      echo "[error] ORCA package was found but installation failed."
      echo "[hint] See installer log: ${INSTALLER_LOG}"
      tail -n 40 "${INSTALLER_LOG}" || true
      exit 4
    elif [[ "${ALLOW_MOCK_ORCA}" == "1" ]]; then
      create_mock_orca
    else
      echo "[error] Could not install ORCA from assets or ORCA_URL."
      echo "[hint] Put installer/archive in: ${ASSETS_DIR}"
      echo "[hint] Accepted patterns: orca*_linux*x86-64*shared*.run or .tar.xz"
      exit 2
    fi
  fi
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

echo "[setup] Done. ORCA path: ${ORCA_HOME}/orca"
