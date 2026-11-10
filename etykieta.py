"""Etykieta (zawieszka) na prezent, POZIOMA: napis „Dla” i pod nim imię wpisane przez użytkownika, otwór Ø 4,2 mm na sznurek z lewej strony.
Płytka 2 mm + wypukła ramka, pierścień wokół otworu i napis (0,8 mm), czcionka Poppins Bold (SIL OFL; podzbiór łaciński z polskimi znakami,
fonts/Poppins-Bold-subset.ttf). Szerokość etykiety dopasowuje się do imienia (min. 60 mm), wysokość 32 mm (rośnie przy bardzo dużych literach).
Druk NA PŁASKO, napisem do góry, bez podpór (same pionowe ścianki na płycie). Wskazówka: zmiana filamentu na warstwie 2,0 mm daje napis w innym kolorze.
Ten sam algorytm działa w artefakcie „Świąteczne dodatki” (artifact/swieta_core.js): STL z przeglądarki = STL z tego skryptu.
  python3 etykieta.py Ania Tomek     -> out/etykieta_ania.stl, out/etykieta_tomek.stl
  python3 etykieta.py --cap 12 "Babcia Ela"   -> wyższe litery imienia (7-15 mm)"""
import os, sys, math, re, argparse
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

FONT_FILE = os.path.join(HERE, "fonts", "Poppins-Bold-subset.ttf")
PT = 2.0                         # grubość płytki [mm]
RAISE = 0.8                      # wypukłość ramki, pierścienia i napisu [mm]
HOLE_D = 4.2                     # otwór na sznurek [mm]
RING_W = 2.2                     # materiał wokół otworu [mm]
HOLE_X = 6.4                     # środek otworu od lewego brzegu [mm]
RIM_IN, RIM_W = 1.4, 1.0         # ramka: odsunięcie od brzegu i szerokość [mm]
CORNER = 5.0                     # promień rogów płytki [mm]
TEXT_M = 1.4                     # odstęp napisu od ramki / pierścienia [mm]
H_MIN, W_MIN = 32.0, 60.0        # najmniejsza wysokość i szerokość [mm]
CAP_DLA_MIN = 6.0                # wysokość wielkiej litery „Dla” (min.; 0,5 wysokości imienia) [mm]
GAP = 3.0                        # odstęp między „Dla” a imieniem [mm]
TRACK = 0.06                     # dodatkowy odstęp liter (w wysokościach wielkiej litery)
CAP_DEFAULT, CAP_MIN, CAP_MAX = 11.0, 7.0, 15.0
CURVE_N = 6                      # odcinków na krzywą kwadratową konturu litery
ARC_N = 16                       # odcinków na ćwiartkę rogu
PETG = 1.27


# ---------------------------------------------------------------------------------------------- czcionka
class _Pen(BasePen):
    def __init__(self, gs):
        super().__init__(gs); self.rings = []; self.cur = None

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, CURVE_N + 1):
            t = i / CURVE_N
            self.cur.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))

    def _closePath(self):
        if self.cur and len(self.cur) > 2:
            self.rings.append(self.cur)
        self.cur = None

    _endPath = _closePath


class Font:
    def __init__(self, path=FONT_FILE):
        self.f = TTFont(path)
        self.upm = self.f["head"].unitsPerEm
        self.cmap = self.f.getBestCmap()
        self.gs = self.f.getGlyphSet()
        self.hmtx = self.f["hmtx"]
        self.cap = float(self.f["OS/2"].sCapHeight)

    def glyph(self, ch, k):
        """wielokąt znaku (shapely) w skali k [mm / jednostkę fontu], linia bazowa y = 0, początek x = 0; zwraca (wielokąt, advance)"""
        name = self.cmap.get(ord(ch))
        if name is None:
            name = self.cmap.get(ord("?"))
        pen = _Pen(self.gs); self.gs[name].draw(pen)
        outers, holes = [], []
        for r in pen.rings:
            P = Polygon([(x * k, y * k) for x, y in r]).buffer(0)
            area2 = sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))
            (holes if area2 > 0 else outers).append(P)                   # TrueType: kontury zewnętrzne zgodnie z ruchem wskazówek (pole < 0)
        g = unary_union(outers) if outers else Polygon()
        if holes:
            g = g.difference(unary_union(holes))
        return g, self.hmtx[name][0] * k


def text_poly(font, s, cap_h):
    """napis w jednej linii: wysokość wielkiej litery = cap_h, linia bazowa y = 0, od x = 0; zwraca (wielokąt, szerokość)"""
    k = cap_h / font.cap
    x, parts = 0.0, []
    for ch in s:
        g, adv = font.glyph(ch, k)
        if not g.is_empty:
            parts.append(affinity.translate(g, x, 0))
        x += adv + TRACK * cap_h
    x -= TRACK * cap_h
    return (unary_union(parts) if parts else Polygon()), x


def rrect(cx, cy, w, h, r, n=ARC_N):
    """prostokąt z zaokrąglonymi rogami (wielokąt CCW)"""
    r = min(r, w / 2 - 1e-6, h / 2 - 1e-6)
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return Polygon(pts)


def circle(cx, cy, r, n=64):
    return Polygon([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)])


def layout(font, name, cap):
    """wymiary i położenie napisów; zwraca dict"""
    cap = float(min(max(cap, CAP_MIN), CAP_MAX))
    cap_d = max(CAP_DLA_MIN, 0.5 * cap)
    gn, wn = text_poly(font, name, cap)
    gd, wd = text_poly(font, "Dla", cap_d)
    wt = max(wn, wd)
    M = RIM_IN + RIM_W + TEXT_M
    H = max(H_MIN, 2 * M + cap_d + GAP + 1.32 * cap)                          # 1,32: wielka litera + znaki pod linią (ogonki, g, y)
    x_h = HOLE_X
    zone0 = HOLE_X + HOLE_D / 2 + RING_W + TEXT_M                             # od lewego brzegu: pierścień i odstęp
    W = max(W_MIN, zone0 + wt + M)
    return dict(cap=cap, cap_d=cap_d, gn=gn, wn=wn, gd=gd, wd=wd, wt=wt, M=M, H=H, W=W, zone0=zone0)


def build_label(name, cap=CAP_DEFAULT, font=None):
    font = font or Font()
    L = layout(font, name, cap)
    W, H = L["W"], L["H"]
    S = rrect(0, 0, W, H, CORNER)
    hx, hy = -W / 2 + HOLE_X, 0.0
    hole = circle(hx, hy, HOLE_D / 2, 48)
    ring = circle(hx, hy, HOLE_D / 2 + RING_W, 64)
    rim = rrect(0, 0, W - 2 * RIM_IN, H - 2 * RIM_IN, CORNER - RIM_IN).difference(rrect(0, 0, W - 2 * (RIM_IN + RIM_W), H - 2 * (RIM_IN + RIM_W), CORNER - RIM_IN - RIM_W))
    xc = -W / 2 + L["zone0"] + (W - L["zone0"] - L["M"] - 0.0) / 2 - 0.0       # środek strefy napisu
    xc = -W / 2 + L["zone0"] + (W - L["zone0"] - L["M"]) / 2
    top = H / 2 - L["M"]
    y_dla = top - L["cap_d"]                                                  # linia bazowa „Dla”
    y_name = y_dla - GAP - L["cap"]                                            # linia bazowa imienia
    x_left = xc - L["wt"] / 2
    dla = affinity.translate(L["gd"], x_left, y_dla)
    nm = affinity.translate(L["gn"], x_left + (L["wt"] - L["wn"]) / 2, y_name)
    raised = unary_union([rim, ring, dla, nm]).difference(hole)
    plate = S.difference(hole)
    from foremki_piernik import prism
    parts = [prism(plate, 0.0, PT)] + [prism(g, PT, PT + RAISE) for g in (raised.geoms if hasattr(raised, "geoms") else [raised])]
    m = trimesh.boolean.union(parts, engine="manifold")
    m.merge_vertices(); m.remove_unreferenced_vertices()
    info = dict(W=W, H=H, hole=(hx, hy), cap=L["cap"], plate_area=plate.area, raised_area=raised.area, volume=plate.area * PT + raised.area * RAISE)
    return m, info


def slug(s):
    t = s.lower().translate(str.maketrans("ąćęłńóśźż", "acelnoszz"))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_") or "imie"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", default=["Ania"], help="imiona (każde = osobna etykieta)")
    ap.add_argument("--cap", type=float, default=CAP_DEFAULT, help=f"wysokość wielkiej litery imienia [mm], {CAP_MIN:g}-{CAP_MAX:g}")
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    font = Font()
    ok = True
    from meshclean import clean_degenerate
    for n in a.names:
        m, info = build_label(n, a.cap, font)
        m, ci = clean_degenerate(m)
        path = os.path.join(HERE, "out", f"etykieta_{slug(n)}.stl"); m.export(path)
        comps = len(m.split(only_watertight=False))
        nrm = m.face_normals; zc = m.triangles_center[:, 2]
        oh = float(m.area_faces[(nrm[:, 2] < -math.sin(math.radians(55))) & (zc > 0.6)].sum())
        good = m.is_watertight and comps == 1 and oh < 1.0 and abs(m.volume - info["volume"]) < 0.01 * info["volume"]
        ok &= good
        print(f"etykieta_{slug(n)}.stl „Dla {n}”: {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.1f} mm, litery imienia {info['cap']:g} mm, {m.volume / 1000:.1f} cm3 = {m.volume / 1000 * PETG:.1f} g PETG | "
              f"szczelna {m.is_watertight}, składowe {comps}, nawis>55: {oh:.1f} mm2, V {m.volume:.0f} vs pola {info['volume']:.0f} -> {'PASS' if good else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
