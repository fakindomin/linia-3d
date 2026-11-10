"""Foremki do pierników (5 szt.): choinka, renifer, bałwan, piernikowy ludzik, gwiazdka. Obrysy 2D w jednym miejscu (funkcje shape_*),
z których korzystają też zawieszki (zawieszki.py).
Foremka: ścianka 1,2 mm wokół obrysu ciasta (obrys = WNĘTRZE ścianki, pionowe), kołnierz do dociskania (5 mm szerokości, 2 mm grubości),
ostrze zwężone na ostatnich 2 mm do 0,45 mm od strony zewnętrznej (świadomy wyjątek od minimum 0,8 mm; verify_print ostrzega o ok. 3% powierzchni). Druk: kołnierzem do stołu, ostrzem do góry, bez podpór
(ściany pionowe, zwężenie ostrza skierowane w górę, kołnierz leży na stole).
Obrysy (wysokość ciasta): choinka 90 mm (czubek 60° jak w choinka_miska.py), renifer 90 mm (głowa + poroże 3-poziomowe + uszy-liście
z renifer_kregiel.py, parametry uszu jak w jajko_renifer.py), bałwan 95 (kapelusz, szalik, marchewka), ludzik 90, gwiazdka 80; narożniki zaokrąglone (wypukłe 1,5-2, wklęsłe 2,5 mm).
  python3 foremki_piernik.py   -> out/foremka_{choinka,renifer,balwan,ludzik,gwiazdka}.stl + out/foremki_piernik.png
Uwaga: wydruk FDM nie jest materiałem bezpiecznym dla żywności na stałe (szczeliny między warstwami); do krótkiego kontaktu z ciastem, myć ręcznie."""
import os, sys, math, time
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

# ---- parametry foremki (jedna definicja; Python = źródło prawdy) ----
WALL = 1.2                      # ścianka [mm] (3 ścieżki dyszy 0,4)
EDGE = 0.45                     # grubość ostrza na samej górze [mm]
TAPER = 2.0                     # wysokość zwężenia ostrza [mm]
H_TOT = 16.0                    # wysokość całkowita (od kołnierza do ostrza) [mm]
FL_T, FL_W = 2.0, 5.0           # kołnierz: grubość i szerokość poza ścianką [mm]
STEPS = 8                       # schodki zwężenia (po 0,25 mm)
R_CONV, R_REFL = 1.5, 2.5       # zaokrąglenia obrysu ciasta: wypukłe (czubki) i wklęsłe (kąty)
PETG = 1.27                     # g/cm3
SIZES = dict(choinka=90.0, renifer=90.0, balwan=95.0, ludzik=90.0, gwiazdka=80.0)     # wysokość obrysu ciasta [mm]
NAMES = dict(choinka="choinka", renifer="renifer", balwan="bałwan", ludzik="piernikowy ludzik", gwiazdka="gwiazdka")
LEAF_REF = dict(leafAng=21.0, leafPos=51.0, leafL=16.0, leafW=10.0)     # uszy renifera jak w jajko_renifer.py (zatwierdzone)


# ---------------------------------------------------------------------------------------------- obrysy 2D (y do góry, mm)
def rounded(P, rc=R_CONV, rr=R_REFL, qs=16):
    """zaokrągla narożniki: otwarcie (wypukłe, rc) i domknięcie (wklęsłe, rr)"""
    q = P.buffer(-rc, join_style=1, quad_segs=qs).buffer(rc, join_style=1, quad_segs=qs)
    q = q.buffer(rr, join_style=1, quad_segs=qs).buffer(-rr, join_style=1, quad_segs=qs)
    if q.geom_type == "MultiPolygon":
        q = max(q.geoms, key=lambda g: g.area)
    return q


def fit(P, height):
    """skala do zadanej wysokości obrysu i środek ramki w (0, 0)"""
    x0, y0, x1, y1 = P.bounds
    P = affinity.scale(P, height / (y1 - y0), height / (y1 - y0), origin=(0, 0))
    x0, y0, x1, y1 = P.bounds
    return affinity.translate(P, -(x0 + x1) / 2, -(y0 + y1) / 2)


def shape_choinka():
    import choinka_miska as CM                           # obrys oryginału (3 piętra, półki, pień) z czubkiem 60°
    return CM.orig_outline(1.0)


def shape_renifer():
    """głowa (okrąg R = headR) + dwa poroża 3-poziomowe + dwa uszy-liście; widok z przodu z części renifer_kregiel.py"""
    import renifer_kregiel as RK
    from skimage import measure
    P = {**RK.params(), **LEAF_REF}

    def outline(fp, fr, mirror):
        cv, m, polys = fp.cv, fp.cv.mask(), []
        for c in measure.find_contours(np.pad(m.astype(float), 1), 0.5):
            a = cv.a0 + (c[:, 1] - 1 + 0.5) * cv.res
            b = cv.b0 + (c[:, 0] - 1 + 0.5) * cv.res
            if mirror:
                a = -a
            X = fr.O[0] + a * fr.A[0] + b * fr.B[0]
            Z = fr.O[2] + a * fr.A[2] + b * fr.B[2]
            if len(X) > 8:
                polys.append(Polygon(np.column_stack([X, Z])).buffer(0))
        return unary_union(polys)
    parts = []
    for s in (+1, -1):
        ap = RK.ant_part(s < 0, P, res=0.1)
        parts.append(outline(ap, RK.ant_frame(s, P), ap.mirror))
        parts.append(outline(RK.leaf_part(P, res=0.1), RK.leaf_frame(s, P), False))
    parts.append(Point(0, P["headZ"]).buffer(P["headR"], 128))
    return unary_union(parts)


def shape_balwan():
    circ = [(0, 25, 25), (0, 59, 19), (0, 84, 14)]                          # trzy kule (x, y, R); szyje 30 i 21 mm
    hat = unary_union([box(-17, 95.0, 17, 99.0), box(-10, 98.0, 10, 111.0)])             # rondel i kapelusz
    scarf = box(-14, 70.5, 14, 75.5)                                                     # szalik (wystaje ok. 3 mm poza szyję)
    nose = Polygon([(10, 88), (26, 84), (10, 80)])                                       # marchewka (po zaokrągleniu ok. 6 mm)
    return unary_union([Point(x, y).buffer(R, 96) for x, y, R in circ] + [hat, scarf, nose])


def shape_ludzik():
    cap = lambda p, q, r: LineString([p, q]).buffer(r, 48)
    parts = [Point(0, 80).buffer(10.5, 96), cap((0, 48), (0, 66), 12.0)]
    for s in (+1, -1):
        parts += [cap((s * 8, 61), (s * 31, 70), 5.5), cap((s * 6.5, 50), (s * 14.5, 8), 6.5)]
    return unary_union(parts)


def shape_gwiazdka(ri=0.5):
    pts = [((1.0 if k % 2 == 0 else ri) * math.cos(math.radians(90 + 36 * k)), (1.0 if k % 2 == 0 else ri) * math.sin(math.radians(90 + 36 * k))) for k in range(10)]
    return Polygon(pts)


SHAPES = dict(choinka=shape_choinka, renifer=shape_renifer, balwan=shape_balwan, ludzik=shape_ludzik, gwiazdka=shape_gwiazdka)


def dough(name):
    """obrys ciasta (wnętrze ścianki): zaokrąglony, w skali SIZES"""
    return fit(rounded(fit(SHAPES[name](), SIZES[name]), R_CONV if name != "gwiazdka" else 1.5), SIZES[name]).simplify(0.01)


# ---------------------------------------------------------------------------------------------- bryła foremki
def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def cutter(S):
    """foremka z obrysu ciasta S: kołnierz (z 0..FL_T) + ścianka (do H_TOT - TAPER) + zwężone ostrze; wnętrze S otwarte"""
    flange = S.buffer(WALL + FL_W, join_style=1, quad_segs=16).difference(S)
    wall = S.buffer(WALL, join_style=1, quad_segs=16).difference(S)
    parts = [prism(flange, 0.0, FL_T), prism(wall, FL_T, H_TOT - TAPER)]
    dz = TAPER / STEPS
    for i in range(STEPS):
        off = WALL - (WALL - EDGE) * (i + 1) / STEPS
        parts.append(prism(S.buffer(off, join_style=1, quad_segs=16).difference(S), H_TOT - TAPER + i * dz, H_TOT - TAPER + (i + 1) * dz))
    m = trimesh.boolean.union(parts, engine="manifold")
    m.merge_vertices(); m.remove_unreferenced_vertices()
    return m


def overhang_55(m):
    n = m.face_normals; zc = m.triangles_center[:, 2]
    return float(m.area_faces[(n[:, 2] < -math.sin(math.radians(55))) & (zc > 0.6)].sum())


def feature_check(S, r=2.4):
    """najcieńsze elementy ciasta: pole tracone przy otwarciu promieniem r (elementy węższe niż 2r = 4,8 mm) w % pola"""
    o = S.buffer(-r, join_style=1).buffer(r, join_style=1)
    return 100.0 * S.difference(o).area / S.area


def main():
    t0 = time.time()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    fig, ax = plt.subplots(1, 5, figsize=(17, 4.4))
    ok = True
    for a, name in zip(ax, SHAPES):
        S = dough(name)
        m = cutter(S)
        from meshclean import clean_degenerate                       # STANDARD: zwiń mikro-trójkąty przed zapisem (bez otwierania siatki)
        m, ci = clean_degenerate(m)
        if ci["before"]:
            print(f"  (foremka_{name}.stl: zdegenerowane trojkaty {ci['before']} -> {ci['after']}, dV = {ci['dvol']:+.2e} mm3)")
        x0, y0, x1, y1 = S.bounds
        path = os.path.join(HERE, "out", f"foremka_{name}.stl"); m.export(path)
        comps = len(m.split(only_watertight=False))
        oh = overhang_55(m)
        ok_i = m.is_watertight and comps == 1 and oh < 1.0 and m.volume > 0
        ok &= ok_i
        print(f"foremka_{name}.stl: ciasto {x1 - x0:.0f} x {y1 - y0:.0f} mm (pole {S.area / 100:.0f} cm2), foremka {m.extents[0]:.0f} x {m.extents[1]:.0f} x {m.extents[2]:.1f} mm | "
              f"szczelna {m.is_watertight}, składowe {comps}, tr. {len(m.faces):,}, {m.volume / 1000:.1f} cm3 = {m.volume / 1000 * PETG:.0f} g PETG | "
              f"nawis>55: {oh:.1f} mm2 | elementy < 4,8 mm: {feature_check(S):.2f}% pola -> {'PASS' if ok_i else 'FAIL'}")
        outer = S.buffer(WALL + FL_W, join_style=1, quad_segs=16)
        a.fill(*outer.exterior.xy, fc="#e8c9a0", ec="#7a4a12", lw=.8)
        a.fill(*S.buffer(WALL, join_style=1, quad_segs=16).exterior.xy, fc="#b9764a", ec="#7a4a12", lw=.6)
        a.fill(*S.exterior.xy, fc="#fff7e6", ec="#7a4a12", lw=.6)
        a.set_aspect("equal"); a.set_title(f"{NAMES[name]}: ciasto {x1 - x0:.0f} x {y1 - y0:.0f} mm", fontsize=9); a.axis("off")
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "out", "foremki_piernik.png"), dpi=70)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
