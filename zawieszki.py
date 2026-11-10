"""Zawieszki (etykiety) na prezenty: płaska płytka 2 mm z otworem Ø 4,2 mm na sznurek, wypukła ramka 0,8 mm wzdłuż brzegu i wokół otworu,
wypukły napis (DejaVu Sans Bold, polskie znaki). Kształty: prostokąt ze ściętymi rogami, bombka (koło), choinka, gwiazdka, renifer
(te same obrysy co w foremki_piernik.py). Druk NA PŁASKO, napisem do góry, bez podpór (wszystko to pionowe ścianki na płycie).
  python3 zawieszki.py                 -> out/zawieszka_{prostokat,bombka,choinka,gwiazdka,renifer}.stl z napisami 'DLA:' i 'OD:'
  python3 zawieszki.py Ania Tomek      -> out/zawieszka_ania.stl, out/zawieszka_tomek.stl (prostokąt, napis 'DLA:' i imię)
Napis dobiera się sam: największa wysokość liter (7 -> 4,5 mm), przy której obie linie mieszczą się wewnątrz ramki i pod otworem."""
import os, sys, math, time, re
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import foremki_piernik as FP

PT = 2.0                         # grubość płytki [mm]
RAISE = 0.8                      # wypukłość ramki i napisu [mm]
HOLE_D = 4.2                     # otwór na sznurek [mm]
RING_W = 2.2                     # materiał wokół otworu [mm]
RIM_IN, RIM_W = 1.4, 1.0         # ramka: odsunięcie od brzegu i szerokość [mm]
TEXT_MARGIN = 1.2                # odstęp napisu od ramki [mm]
LINE_GAP = 3.6                   # odstęp między liniami napisu [mm]
H_MAX, H_MIN, H_STEP = 7.0, 4.5, 0.25
FONT = FontProperties(family="DejaVu Sans", weight="bold")
HEIGHTS = dict(choinka=80.0, gwiazdka=76.0, renifer=84.0)      # wysokość zawieszki z obrysów foremek [mm]


def shape_prostokat():
    return FP.rounded(Polygon([(-35, -23), (35, -23), (35, 11), (24, 23), (-24, 23), (-35, 11)]), 4.0, 1.0)


def shape_bombka():
    return Point(0, 0).buffer(30.0, 128)


def tag_shape(name):
    if name == "prostokat":
        return shape_prostokat()
    if name == "bombka":
        return shape_bombka()
    S = FP.SHAPES[name]()
    S = FP.fit(FP.rounded(FP.fit(S, HEIGHTS[name]), FP.R_CONV if name != "gwiazdka" else 1.5), HEIGHTS[name])
    return S


def text_poly(s, cap_h):
    """napis jako wielokąt (środek w (0,0)): wysokość wielkiej litery = cap_h; dziury w literach przez XOR"""
    ref = TextPath((0, 0), "H", size=10, prop=FONT).get_extents()
    k = cap_h / ref.height
    tp = TextPath((0, 0), s, size=10 * k, prop=FONT)
    g = Polygon()
    for ring in tp.to_polygons():
        if len(ring) >= 3:
            g = g.symmetric_difference(Polygon(ring).buffer(0))
    if g.is_empty:
        return g
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, -(ref.y0 * k + ref.height * k / 2))      # środek pionowy = środek wielkiej litery


def find_hole(S):
    """otwór: na osi symetrii (x = 0), najwyżej jak się da, tak by wokół mieścił się pierścień RING_W; zwraca środek"""
    inner = S.buffer(-(HOLE_D / 2 + RING_W + 0.6))
    x0, y0, x1, y1 = S.bounds
    for y in np.arange(y1, y0, -0.25):
        if inner.contains(Point(0.0, y)):
            return (0.0, float(y))
    raise RuntimeError("brak miejsca na otwór")


def place_text(S, hole, lines):
    """szuka największej wysokości liter i najwyższego położenia bloku napisu, przy których cały napis leży wewnątrz ramki
    (S zmniejszone o RIM_IN + RIM_W + TEXT_MARGIN) i poza pierścieniem otworu; zwraca (wielokąt napisu, wysokość liter) albo (None, None)"""
    ok_area = S.buffer(-(RIM_IN + RIM_W + TEXT_MARGIN)).difference(Point(hole).buffer(HOLE_D / 2 + RING_W + RIM_W + TEXT_MARGIN))
    x0, y0, x1, y1 = S.bounds
    h = H_MAX
    while h >= H_MIN - 1e-9:
        glyphs = [text_poly(s, h) for s in lines]
        total = h * len(lines) + LINE_GAP * (len(lines) - 1)
        for yt in np.arange(hole[1] - HOLE_D / 2 - RING_W - 2.0, y0 + total, -0.5):              # górna krawędź bloku, od otworu w dół
            parts, y = [], yt - h / 2
            for g in glyphs:
                parts.append(affinity.translate(g, 0, y))
                y -= h + LINE_GAP
            blk = unary_union(parts)
            if ok_area.contains(blk):
                return blk, h
        h -= H_STEP
    return None, None


def build_tag(S, lines):
    hole = find_hole(S)
    txt, h = place_text(S, hole, lines) if lines else (None, None)
    hole_poly = Point(hole).buffer(HOLE_D / 2, 48)
    ring = Point(hole).buffer(HOLE_D / 2 + RING_W, 64)
    rim = S.buffer(-RIM_IN).difference(S.buffer(-(RIM_IN + RIM_W)))
    raised = unary_union([g for g in (rim, ring, txt) if g is not None and not g.is_empty]).intersection(S.buffer(-0.3)).difference(hole_poly)
    plate = S.difference(hole_poly)
    parts = [FP.prism(plate, 0.0, PT)] + [FP.prism(g, PT, PT + RAISE) for g in (raised.geoms if hasattr(raised, "geoms") else [raised])]
    m = trimesh.boolean.union(parts, engine="manifold")
    m.merge_vertices(); m.remove_unreferenced_vertices()
    return m, hole, h


def slug(s):
    t = s.lower().translate(str.maketrans("ąćęłńóśźż", "acelnoszz"))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_") or "imie"


def main(argv):
    t0 = time.time()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    jobs = []
    if argv:
        jobs = [(f"zawieszka_{slug(n)}.stl", "prostokat", ["DLA:", n]) for n in argv]
    else:
        jobs = [(f"zawieszka_{k}.stl", k, ["DLA:", "OD:"]) for k in ("prostokat", "bombka", "choinka", "gwiazdka", "renifer")]
    ok = True
    for fn, shp, lines in jobs:
        S = tag_shape(shp)
        m, hole, h = build_tag(S, lines)
        from meshclean import clean_degenerate                       # STANDARD: zwiń mikro-trójkąty przed zapisem (bez otwierania siatki)
        m, ci = clean_degenerate(m)
        if ci["before"]:
            print(f"  ({fn}: zdegenerowane trojkaty {ci['before']} -> {ci['after']}, dV = {ci['dvol']:+.2e} mm3)")
        path = os.path.join(HERE, "out", fn); m.export(path)
        x0, y0, x1, y1 = S.bounds
        comps = len(m.split(only_watertight=False))
        n = m.face_normals; zc = m.triangles_center[:, 2]
        oh = float(m.area_faces[(n[:, 2] < -math.sin(math.radians(55))) & (zc > 0.6)].sum())
        good = m.is_watertight and comps == 1 and oh < 1.0 and h is not None
        ok &= good
        print(f"{fn}: {m.extents[0]:.0f} x {m.extents[1]:.0f} x {m.extents[2]:.1f} mm, {m.volume / 1000:.1f} cm3 = {m.volume / 1000 * FP.PETG:.1f} g PETG | otwór Ø {HOLE_D} w ({hole[0]:.1f}; {hole[1]:.1f}) | "
              f"napis: {'wys. liter %.2f mm' % h if h else 'BRAK MIEJSCA'} | szczelna {m.is_watertight}, składowe {comps}, nawis>55: {oh:.1f} mm2 -> {'PASS' if good else 'FAIL'}")
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
