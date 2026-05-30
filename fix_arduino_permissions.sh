#!/usr/bin/env bash
set -euo pipefail

RULE_FILE="/etc/udev/rules.d/99-arduino-nano-esp32.rules"
RULE='SUBSYSTEM=="usb", ATTR{idVendor}=="2341", ATTR{idProduct}=="0070", MODE="0666", TAG+="uaccess"'

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ejecuta este script con sudo:"
  echo "sudo $0"
  exit 1
fi

printf '%s\n' "${RULE}" > "${RULE_FILE}"
udevadm control --reload-rules
udevadm trigger

while read -r bus device _rest; do
  bus="${bus#Bus }"
  device="${device#Device }"
  device="${device%:}"
  path="/dev/bus/usb/${bus}/${device}"
  if [[ -e "${path}" ]]; then
    chmod a+rw "${path}"
    echo "Permisos aplicados a ${path}"
  fi
done < <(lsusb | awk '/2341:0070/ {print "Bus " $2, "Device " $4, $0}')

echo "Regla instalada en ${RULE_FILE}"
echo "Desconecta y vuelve a conectar el Arduino Nano ESP32."
