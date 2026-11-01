#!/usr/bin/env bash
# Holt die ETSI-/Vanetza-ASN.1-Spezifikationen (BSD-3 / ETSI-Lizenz) nach ./asn
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p asn && cd asn
clone() { [ -d "$1" ] || git clone -q --depth 1 --branch "$2" "$3" "$1"; }
F=https://forge.etsi.org/rep/ITS/asn1
clone vanetza  master  https://github.com/riebl/vanetza.git   # CAM v1.4.1, DENM v1.3.1, CDD v1.3.1, IEEE1609.2
clone cdd2     V2.2.1  $F/cdd_ts102894_2.git                  # CDD v2 (fuer SPATEM/MAPEM)
clone is_ts    v2.2.1  $F/is_ts103301.git                     # SPATEM/MAPEM + DSRC (ISO TS 19091)
echo "ASN.1 bereit in $(pwd)"
