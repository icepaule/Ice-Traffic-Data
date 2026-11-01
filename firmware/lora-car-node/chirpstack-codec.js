// ChirpStack-v4-Payload-Codec fuer den Auto-Knoten (Nutzlast v1, 25 Byte, Big Endian).
// Layout: siehe docs/10-lorawan.md. Testen: node firmware/lora-car-node/test/codec.test.js
function u16(b, i) { return (b[i] << 8) | b[i + 1]; }
function i32(b, i) { return (b[i] << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3]; }
function decode(bytes) {
  if (!bytes || bytes.length < 25) throw new Error('payload too short');
  if (bytes[0] !== 1) throw new Error('unsupported payload version ' + bytes[0]);
  var f = bytes[1];
  var fix = !!(f & 1);
  return {
    version: 1,
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
}
function decodeUplink(input) {
  try { return { data: decode(input.bytes) }; } catch (e) { return { errors: [String(e.message || e)] }; }
}
function Decoder(bytes, port) { return decode(bytes); }
if (typeof module !== 'undefined') module.exports = { decode: decode, decodeUplink: decodeUplink, Decoder: Decoder };
