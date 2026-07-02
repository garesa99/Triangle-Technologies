#!/usr/bin/env bash
# Install the Triangle node-agent on a Raspberry Pi (Debian/Raspberry Pi OS).
# Installs only the CORE deps; add hardware driver deps per what THIS node has (see requirements.txt).
set -euo pipefail

PREFIX=/opt/triangle/node-agent
CFG=/etc/triangle

echo "==> Triangle node-agent installer"
if [[ $EUID -ne 0 ]]; then echo "run with sudo"; exit 1; fi

id triangle &>/dev/null || useradd --system --home "$PREFIX" --shell /usr/sbin/nologin triangle

mkdir -p "$PREFIX" "$CFG" /var/lib/triangle
cp -r "$(dirname "$0")/"* "$PREFIX/"

python3 -m venv "$PREFIX/.venv"
"$PREFIX/.venv/bin/pip" install --upgrade pip
"$PREFIX/.venv/bin/pip" install numpy httpx pyyaml zeroconf

echo "==> Optional hardware drivers (uncomment in requirements.txt or install now):"
echo "    sounddevice pyserial pyubx2   (acoustic / Remote-ID / GNSS)"
echo "    SoapySDR via apt: sudo apt install soapysdr-tools python3-soapysdr soapysdr-module-hackrf"

if [[ ! -f "$CFG/config.yaml" ]]; then
  cp "$PREFIX/config.example.yaml" "$CFG/config.yaml"
  echo "==> Wrote $CFG/config.yaml — EDIT node_id, position, brain_url, token before starting."
fi

chown -R triangle:triangle "$PREFIX" /var/lib/triangle "$CFG"
cp "$PREFIX/triangle-node.service" /etc/systemd/system/
systemctl daemon-reload
echo "==> Installed. Edit $CFG/config.yaml, then: sudo systemctl enable --now triangle-node"
