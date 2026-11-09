// ChirpStack-v4-Payload-Codec fuer den Auto-Knoten (Nutzlast v1 = 25 Byte, v2 = 36 Byte mit Funkstrecke, Big Endian).
// Layout: siehe docs/10-lorawan.md. Testen: node firmware/lora-car-node/test/codec.test.js
function u16(b, i) { return (b[i] << 8) | b[i + 1]; }
function i32(b, i) { return (b[i] << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3]; }
function i8(v) { return v > 127 ? v - 256 : v; }
function decode(bytes) {
  if (!bytes || bytes.length < 25) throw new Error('payload too short');
  var ver = bytes[0];
  if (ver !== 1 && ver !== 2) throw new Error('unsupported payload version ' + ver);
  if (ver === 2 && bytes.length < 36) throw new Error('payload too short');
  var f = bytes[1];
  var fix = !!(f & 1);
  var o = {
    version: ver,
    gps_fix: fix,
    denm_new: !!(f & 2),
    bridge_alive: !!(f & 4),
    latitude: fix ? i32(bytes, 2) / 1e6 : null,
    longitude: fix ? i32(bytes, 6) / 1e6 : null,
    speed_kmh: bytes[10],
    satellites: bytes[11],
    cam: u16(bytes, 12),
    denm: u16(bytes, 14),
    spatem: u16(bytes, 16),
    mapem: u16(bytes, 18),
    secured: u16(bytes, 20),
    other: u16(bytes, 22),
    uptime_min: bytes[24] * 10
  };
  if (ver === 2) {
    var avg = i8(bytes[25]);  // 127 = unbekannt (kein ITS6 / kein Paket im Intervall)
    o.sniffer_rssi_avg = avg === 127 ? null : avg;
    o.sniffer_rssi_min = avg === 127 ? null : i8(bytes[26]);
    o.sniffer_rssi_max = avg === 127 ? null : i8(bytes[27]);
    o.sniffer_rx_err = u16(bytes, 28);
    o.sniffer_unicast = u16(bytes, 30);
    o.sniffer_dropped = u16(bytes, 32);
    o.frames_lost = u16(bytes, 34);
  }
  return o;
}
function decodeUplink(input) {
  try { return { data: decode(input.bytes) }; } catch (e) { return { errors: [String(e.message || e)] }; }
}
function Decoder(bytes, port) { return decode(bytes); }
if (typeof module !== 'undefined') module.exports = { decode: decode, decodeUplink: decodeUplink, Decoder: Decoder };
