"""Kompiliert die ASN.1-Spezifikationen (UPER fuer Nachrichten, OER fuer IEEE 1609.2)."""
import glob
import os

import asn1tools

ASN = os.environ.get("ITS_ASN_DIR", os.path.join(os.path.dirname(__file__), "..", "asn"))


def _p(*a):
    return os.path.join(ASN, *a)


def load():
    van = _p("vanetza", "asn1")
    cdd1 = os.path.join(van, "TS102894-2v131-CDD.asn")
    cdd2 = glob.glob(_p("cdd2", "*.asn"))
    dsrc = [_p("is_ts", f) for f in ("DSRC-region.asn", "DSRC-addgrp-C.asn", "DSRC.asn")]
    s = {
        "CAM": asn1tools.compile_files([cdd1, os.path.join(van, "EN302637-2v141-CAM.asn")], "uper"),
        "DENM": asn1tools.compile_files([cdd1, os.path.join(van, "EN302637-3v131-DENM.asn")], "uper"),
        "SPATEM": asn1tools.compile_files(cdd2 + dsrc + [_p("is_ts", "SPATEM-PDU-Descriptions.asn")], "uper"),
        "MAPEM": asn1tools.compile_files(cdd2 + dsrc + [_p("is_ts", "MAPEM-PDU-Descriptions.asn")], "uper"),
    }
    try:
        s["SEC"] = asn1tools.compile_files(
            [os.path.join(van, "IEEE1609dot2BaseTypes.asn"), os.path.join(van, "IEEE1609dot2.asn")], "oer")
    except Exception:  # Signatur-Huelle optional
        s["SEC"] = None
    return s
