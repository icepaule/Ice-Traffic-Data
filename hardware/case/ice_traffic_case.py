#!/usr/bin/env python3
"""Ice-Traffic-Data: Gehaeuse fuer Traffik-Sniffer (C5), Trafik-CPU (C3), GPS-LoRa (XIAO+Wio), Grove-GPS, Prepboard.
Parametrisch (CadQuery). Alle Masse in mm. Erzeugt STEP (SolidWorks) und STL (Slicer) fuer Unterteil, Deckel und eine
Montage-Ansicht mit Platzhalter-Boards.  Nutzung:  python3 ice_traffic_case.py [ausgabeordner]
Koordinaten: Ursprung = untere linke Innenecke des Unterteils, X = Laenge, Y = Breite, Z = Hoehe ueber dem Innenboden."""
import sys, os
import cadquery as cq

# ---------------- Parameter (hier mit dem Messschieber nachziehen) ----------------
T = 2.4            # Wandstaerke
F = 2.4            # Bodenstaerke
H = 38.0           # Innenhoehe (bis Oberkante Unterteil)
L, W = 118.0, 70.0 # Innenlaenge/-breite
PCB_T = 1.6        # Platinendicke
POST_H = 5.0       # Abstand Boden -> Platinenunterseite (Platz fuer Stiftleisten unten)
TOL = 0.3          # Spiel zwischen Platine und Clip
# Boards (Laenge x Breite) -- ANNAHMEN, bitte messen
C5 = (53.5, 25.4)      # ESP32-C5-DevKitC-1: Laenge gemessen (53,5), Breite laut Espressif 25,4
C3 = (38.9, 25.4)      # ESP32-C3-DevKitM-1: Espressif-Zeichnung (DXF) 25,40 x 38,91
XIAO = (21.0, 17.8)    # XIAO ESP32S3 + Wio-SX1262 (Seeed-Wiki: 21 x 17,8; B2B-Stapel, Gesamthoehe geschaetzt)
GPS = (40.0, 20.0)     # Grove-GPS Air530 (40 x 20 x 13)
PREP = (45.0, 35.0)    # Prepboard: 45 (Y) x 35 (Z, hochkant) nach Angabe
# Bohrungen
D_ANT = 7.0        # Antenne
D_PWR = 11.0       # Stromanschluss
M3_PILOT = 2.8     # Kernloch fuer M3-Schraube in Kunststoff
M3_CLEAR = 3.4
# Positionen (Innenkoordinaten)
X_LEFT = 8.0                      # Beginn der Boards C5/C3 (Eckdomen links)
Y_C5, Y_C3 = 2.0, W - 2.0 - 25.4  # untere Kante C5 / C3; die Luecke dazwischen (ca. 15 mm) ist die Strombuchse (links)
X_PREP = 66.5                     # Mitte des Prepboard-Schlitzes
X_RIGHT = 72.0                    # Beginn GPS
X_XIAO = L - 22.0                 # XIAO sitzt an der rechten Wand (USB-C zur Wand)
Y_XIAO, Y_GPS = 9.0, 40.0         # XIAO ueber der Eckdom-Zone (Y>=7), GPS darueber
Y_ANT_X = 100.0                   # X-Position der Antennenbohrung (Frontwand)
Z_ANT = 12.0
Y_PWR, Z_PWR = W / 2, 16.0         # Stromanschluss an der linken Stirnwand, mittig zwischen C5 und C3

def box(x, y, z, dx, dy, dz):
    return cq.Workplane("XY").box(dx, dy, dz, centered=False).translate((x, y, z))

LEDGE, HOOK = 0.8, 0.7            # Auflage unter / Haken ueber der Platine (Stiftleisten sitzen ab ca. 1 mm Randabstand)
CLIP_W, CLIP_X = 3.0, 1.0         # Clipbreite, Abstand vom Platinenende (Clips sitzen in den Ecken, ausserhalb der Stiftleisten)

def clip(u_edge_y, x, upper, width=CLIP_W, t=1.2):
    """Schnappclip an einer Platinen-Langkante. u_edge_y = Y der Kante, upper=True: Clip liegt bei groesserem Y."""
    zt = POST_H + PCB_T + 0.2
    pts = [(-(TOL + t), 0), (LEDGE, 0), (LEDGE, POST_H), (-TOL, POST_H), (-TOL, zt), (HOOK, zt), (HOOK, zt + 0.5), (-(TOL + t), zt + 1.8)]
    s = -1 if upper else 1
    ps = [(u_edge_y + s * u, z) for u, z in pts]
    return cq.Workplane("YZ").polyline(ps).close().extrude(width).translate((x, 0, 0))

def board_clips(x0, y0, bl, bw):
    r = None
    for xo in (CLIP_X, bl - CLIP_X - CLIP_W):
        for c in (clip(y0, x0 + xo, False), clip(y0 + bw, x0 + xo, True)):
            r = c if r is None else r.union(c)
    return r

def build_base():
    outer = box(-T, -T, -F, L + 2 * T, W + 2 * T, F + H)
    base = outer.cut(box(0, 0, 0, L, W, H + 1))
    # Schraubdomen in den Ecken
    for cx, cy in ((0, 0), (L - 7, 0), (0, W - 7), (L - 7, W - 7)):
        d = box(cx, cy, -0.01, 7, 7, H + 0.01)
        hole = cq.Workplane("XY").circle(M3_PILOT / 2).extrude(14).translate((cx + 3.5, cy + 3.5, H - 14))
        base = base.union(d).cut(hole)
    # Clips
    for (x0, y0, bl, bw) in ((X_LEFT, Y_C5, *C5), (X_LEFT, Y_C3, *C3), (X_XIAO, Y_XIAO, *XIAO), (X_RIGHT, Y_GPS, *GPS)):
        base = base.union(board_clips(x0, y0, bl, bw))
    # Prepboard-Schlitz (hochkant eingeklemmt): zwei Rippen, Spalt = Platinendicke + 0.3
    gap = PCB_T + 0.3
    yc = (W) / 2
    for dx in (-(gap / 2 + 1.5), gap / 2):
        base = base.union(box(X_PREP + dx, yc - 15, 0, 1.5, 30, 12))
    # Bohrungen
    base = base.cut(cq.Workplane("XZ").circle(D_ANT / 2).extrude(T + 1).translate((Y_ANT_X, 1, Z_ANT)))             # Frontwand (Y<0)
    base = base.cut(cq.Workplane("YZ").circle(D_PWR / 2).extrude(T + 1).translate((-T - 0.5, Y_PWR, Z_PWR)))      # linke Stirnwand
    zu = POST_H + PCB_T + 3.0
    for y0, bw, sw in ((Y_C5, C5[1], 24.0), (Y_C3, C3[1], 16.0)):                                                   # USB links (C5: 2 x USB-C, C3: Micro-USB)
        base = base.cut(box(-T - 0.5, y0 + bw / 2 - sw / 2, zu - 5, T + 1, sw, 10))
    base = base.cut(box(L - 0.5, Y_XIAO + XIAO[1] / 2 - 6, zu - 4, T + 1, 12, 8))                                   # USB XIAO rechts
    # Kabelbinder-Schlitze im Boden
    for x in (60.0, 112.0):
        base = base.cut(box(x, 12, -F - 0.5, 3, 16, F + 1)).cut(box(x, 44, -F - 0.5, 3, 16, F + 1))
    return base

def build_lid():
    """Deckel in Einbaulage (Unterseite bei z=H); fuer den Druck wird er gedreht."""
    plate = box(-T, -T, H, L + 2 * T, W + 2 * T, T)
    lip_o = box(0.3, 0.3, H - 2, L - 0.6, W - 0.6, 2)
    lip_i = box(1.5, 1.5, H - 2.1, L - 3.0, W - 3.0, 2.2)
    lip = lip_o.cut(lip_i)
    for cx, cy in ((0, 0), (L - 9, 0), (0, W - 9), (L - 9, W - 9)):
        lip = lip.cut(box(cx, cy, H - 3, 9, 9, 4))
    lid = plate.union(lip)
    gap = PCB_T + 0.3
    yc = W / 2
    for dx in (-(gap / 2 + 1.5), gap / 2):
        lid = lid.union(box(X_PREP + dx, yc - 15, H - 6, 1.5, 30, 6))
    for cx, cy in ((3.5, 3.5), (L - 3.5, 3.5), (3.5, W - 3.5), (L - 3.5, W - 3.5)):
        lid = lid.cut(cq.Workplane("XY").circle(M3_CLEAR / 2).extrude(T + 1).translate((cx, cy, H - 0.5)))
        lid = lid.cut(cq.Workplane("XY").circle(3.0).workplane(offset=1.4).circle(1.7).loft().translate((cx, cy, H + T - 1.4)).translate((0, 0, 0.0)))
    for i in range(8):                                                                                              # Lueftungsschlitze
        lid = lid.cut(box(10 + i * 7.5, W / 2 - 14, H - 0.5, 2.5, 28, T + 1))
    return lid

def to_print(lid):
    return lid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, W, H + T))

def board_dummy(x0, y0, bl, bw, header=True, comp=0.0, color=None):
    b = box(x0, y0, POST_H, bl, bw, PCB_T)
    if header:
        for yy in (y0 + 1.0, y0 + bw - 3.5):
            b = b.union(box(x0 + 4, yy, POST_H - 3, bl - 8, 2.5, 3 + PCB_T + 6.0))
    if comp:
        b = b.union(box(x0 + 3, y0 + 4, POST_H + PCB_T, bl - 10, bw - 8, comp))
    return b

def export(out):
    os.makedirs(out, exist_ok=True)
    base, lid = build_base(), build_lid()
    cq.exporters.export(base, f"{out}/IceTraffic_Gehaeuse_Unterteil.step")
    cq.exporters.export(base, f"{out}/IceTraffic_Gehaeuse_Unterteil.stl", tolerance=0.02)
    lp = to_print(lid)
    cq.exporters.export(lp, f"{out}/IceTraffic_Gehaeuse_Deckel.step")
    cq.exporters.export(lp, f"{out}/IceTraffic_Gehaeuse_Deckel.stl", tolerance=0.02)
    asm = cq.Assembly(name="IceTraffic_Montage")
    asm.add(base, name="Unterteil", color=cq.Color(0.7, 0.75, 0.8, 1))
    asm.add(lid, name="Deckel", color=cq.Color(0.55, 0.6, 0.7, 0.6))
    asm.add(board_dummy(X_LEFT, Y_C5, *C5, comp=3), name="Traffik-Sniffer_C5", color=cq.Color(0.8, 0.1, 0.1, 1))
    asm.add(board_dummy(X_LEFT, Y_C3, *C3, comp=3), name="Trafik-CPU_C3", color=cq.Color(0.1, 0.4, 0.8, 1))
    asm.add(board_dummy(X_XIAO, Y_XIAO, *XIAO, header=False, comp=6), name="GPS-LoRa_XIAO", color=cq.Color(0.1, 0.6, 0.2, 1))
    asm.add(board_dummy(X_RIGHT, Y_GPS, *GPS, header=False, comp=8), name="Grove-GPS", color=cq.Color(0.9, 0.7, 0.1, 1))
    asm.add(box(X_PREP - PREP[1] * 0 - PCB_T / 2, W / 2 - PREP[0] / 2, 2, PCB_T, PREP[0], PREP[1]), name="Prepboard", color=cq.Color(0.9, 0.9, 0.9, 1))
    asm.save(f"{out}/IceTraffic_Montage_mit_Boards.step")
    return base, lid

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    b, l = export(out)
    for n, s in (("Unterteil", b), ("Deckel", l)):
        bb = s.val().BoundingBox()
        print(f"{n}: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, Volumen {s.val().Volume()/1000:.1f} cm3")
