#!/usr/bin/env bash
# Baut beide Firmwares fuer ESP32-C5-DevKitC-1 (N8R8) + ESP32-C3-DevKitM-1.
# Nutzung: ./build.sh            (nur bauen)
#          ./build.sh flash-c5 /dev/ttyACM0   |   ./build.sh flash-c3 /dev/ttyUSB0
set -euo pipefail
cd "$(dirname "$0")"
UPSTREAM=https://github.com/bertrik/its-g5-receiver.git
PIN=45db567c6d0669576e82686293d2a8bc2edbc3e3   # getesteter Upstream-Stand
[ -d src ] || { git clone -q $UPSTREAM src && git -C src checkout -q $PIN && git -C src apply ../0001-devkitm1-uart1.patch && git -C src apply ../0002-its6-rssi-zaehler-baud.patch; }
command -v pio >/dev/null || pip install --user platformio
case "${1:-build}" in
  build)    (cd src/esp32-c5-sniffer && pio run -e devkitc1-n4)
            (cd src/esp32-c3-bridge  && pio run -e devkitm1) ;;
  flash-c5) (cd src/esp32-c5-sniffer && pio run -e devkitc1-n4 -t upload --upload-port "$2") ;;
  flash-c3) (cd src/esp32-c3-bridge  && pio run -e devkitm1 -t uploadfs --upload-port "$2" \
                                     && pio run -e devkitm1 -t upload   --upload-port "$2") ;;
esac
