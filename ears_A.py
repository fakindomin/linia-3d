"""Grupa A: wymienne uszy zwierzakow (mis, kot, lis, sowa) na standardowy czop 5x5x8.
Wszystkie pasuja do korpus_bazowy.stl i do jajko_czapka_gniazda.stl (ta sama podstawa przycieta SDF obu korpusow)."""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *
from build_figurki import FRb, FRe, TRIMS, add_local

AC = (-10.0, 15.0)        # zakres a kanwy (prawe: a>0 = na zewnatrz)


def _poly_from(L, cen, hw, b0=-3.0, n=240):
    bs = np.linspace(b0, L, n)
    left = [(cen(b) - hw(b), b) for b in bs]
    right = [(cen(b) + hw(b), b) for b in bs[::-1]]
    return right[::-1] + left[::-1] if False else [(cen(b) + hw(b), b) for b in bs] + [(cen(b) - hw(b), b) for b in bs[::-1]]


def _ring_from(cv, pts_outer, pts_inner):
    cv.poly(pts_outer, 255)
    cv.poly(pts_inner, 0)


def tri_flat(L, hw0, lean, q=1.0, open_r=1.3, ring_in=2.2, ring_top=0.72, mirror=False, res=0.1):
    """ucho trojkatne (kot/lis): podstawa hw0, wysokosc L, przechylenie wierzcholka 'lean' na zewnatrz, wklesloscia q."""
    def cen(b): return lean * (max(b, 0) / L) ** 1.6

    def hw(b):
        u = max(b, 0) / L
        return hw0 * max(1 - u, 0) ** q
    cv = Canvas(AC[0], AC[1], -4.5, L + 2, res=res)
    cv.poly(_poly_from(L, cen, hw, n=300))
    cv.open_(open_r)
    ring = Canvas(AC[0], AC[1], -4.5, L + 2, res=res)
    b1 = 3.2
    Li = L * ring_top
    inner = lambda b, off: max(hw(b) - off, 0.0)
    bs = np.linspace(b1, Li, 120)
    outer = [(cen(b) + inner(b, ring_in - 0.9 * 0), b) for b in bs] + [(cen(b) - inner(b, ring_in), b) for b in bs[::-1]]
    inn = [(cen(b) + inner(b, ring_in + 0.9), b) for b in bs] + [(cen(b) - inner(b, ring_in + 0.9), b) for b in bs[::-1]]
    ring.poly(outer, 255)
    ring.poly(inn, 0)
    return FlatPart(cv, EAR_T, w=1.0, k=1.5, ring_mask=ring.mask(), ring_h=RING_H, mirror=mirror)


def round_flat(r=6.0, bc=3.6, neck=4.2, mirror=False, res=0.1):
    """ucho misia: okragla kopulka na szyjce, z wglebieniem (wewnetrzne ucho)"""
    L = bc + r
    cv = Canvas(AC[0], AC[1], -4.5, L + 6, res=res)          # zapas > 2 r(close), inaczej wychodzi 'czubek' na krawedzi kanwy
    cv.ellipse(0, bc, r, r, 255)
    cv.rect(-neck, neck, -3.0, bc - 1.0)
    cv.close_(2.2)
    cv.open_(1.0)
    gr = Canvas(AC[0], AC[1], -4.5, L + 6, res=res)
    gr.ellipse(0, bc + 0.3, 3.0, 3.0, 255)
    fp = FlatPart(cv, EAR_T, w=1.0, k=0.9, mirror=mirror)
    dist = ndi.distance_transform_edt(~gr.mask()) * res
    wgt = np.clip((0.7 - dist) / 0.3, 0, 1) * 0.0     # bez wglebienia (wygladalo jak oczy zaby); czysta kopulka
    fp.top = fp.top - np.clip(fp.top - 3.3, 0, None) * wgt      # plaskie dno wglebienia na wysokosci c=3,3 (sciany rownolegle do osi druku)
    return fp, L


def tuft_flat(L=17.0, hw_max=4.5, lean=6.0, mirror=False, res=0.1):
    """pek piorek sowy: liscie odchylony na zewnatrz, z dwiema rysami"""
    def cen(b): return lean * (max(b, 0) / L) ** 1.7

    def hw(b):
        u = max(b, 0) / L
        if u < 0.45:
            return 4.2 + (hw_max - 4.2) * math.sin(math.pi / 2 * u / 0.45)
        t = (u - 0.45) / 0.55
        return hw_max * max(1 - t ** 1.9, 0) ** (1 / 1.9)
    cv = Canvas(AC[0], AC[1], -4.5, L + 2, res=res)
    cv.poly(_poly_from(L, cen, hw, n=300))
    cv.open_(0.9)
    gr = Canvas(AC[0], AC[1], -4.5, L + 2, res=res)
    for off in (-1.5, 1.5):
        pts = [(cen(b) + off * (1 - 0.35 * b / L), b) for b in np.linspace(4.5, 0.82 * L, 40)]
        gr.path(pts, 0.9)
    return FlatPart(cv, EAR_T, w=1.0, k=1.5, groove_mask=gr.mask(), groove_d=0.7, mirror=mirror)


SPECS = {}   # nazwa -> (fabryka(mirror)->FlatPart, L widoczna)


def _reg():
    r_ear, L_mis = round_flat()
    SPECS["mis"] = (lambda m: round_flat(mirror=m)[0], L_mis)
    SPECS["kot"] = (lambda m: tri_flat(22.0, 5.4, 1.2, q=1.0, mirror=m), 22.0)
    SPECS["lis"] = (lambda m: tri_flat(30.0, 5.0, 1.8, q=1.15, open_r=0.8, ring_in=2.0, ring_top=0.7, mirror=m), 30.0)
    SPECS["sowa"] = (lambda m: tuft_flat(16.0, 4.8, 7.0, mirror=m), 16.0)


_reg()


def a_range(side):
    return (-10, 15) if side > 0 else (-15, 10)


def ear_mesh(name, side):
    fac, L = SPECS[name]
    fp = fac(side < 0)
    return part_mesh(fp, TRIMS[side], True, a_range(side), (-9, L + 3), 0.2)


def fit_report(label, tgt, FR, F_body, parts):
    tree = surf_tree(tgt, 600000)
    out = {}
    for s, nm in ((+1, "prawe"), (-1, "lewe")):
        g = to_global(parts[nm], FR[s])
        dd, _ = tree.query(g.vertices)
        a_, b_, c_ = FR[s].to_local(*g.vertices.T)
        V = g.vertices
        Fv = F_body(V[:, 0], V[:, 1], V[:, 2])
        Fv = np.minimum(Fv, -socket_F(a_, b_, c_))
        out[nm] = g
        print(f"   {label} {nm}: podstawa {dd[b_ > 0.4].min():.2f} | czop {dd[b_ < -0.5].min():.2f} mm | w bryle {int((Fv > 0.02).sum())} | wierzch z={V[:, 2].max():.1f}")
    # kolizja prawe/lewe po zlozeniu
    t2 = cKDTree(out["lewe"].vertices)
    d, _ = t2.query(out["prawe"].vertices)
    print(f"   {label}: min. odstep prawe-lewe {d.min():.2f} mm")
    return out


if __name__ == "__main__":
    T0 = time.time()
    body = trimesh.load(OUT + "/korpus_bazowy.stl")
    cap_pl = trimesh.load(OUT + "/jajko_czapka_gniazda.stl")
    cap_pl.apply_translation([0, 0, Z_CAP0])
    names = sys.argv[1:] or list(SPECS)
    for nm in names:
        parts = {}
        for s, side_nm in ((+1, "prawe"), (-1, "lewe")):
            parts[side_nm] = ear_mesh(nm, s)
            save(parts[side_nm], f"ucho_{nm}_{side_nm}.stl", False, "druk na plecach; czop 5x5x8")
        print(f"== {nm}: pasowanie ==")
        fit_report("korpus", body, FRb, bunny_F, parts)
        fit_report("jajko ", cap_pl, FRe, egg_F, parts)
    print(f"czas {time.time() - T0:.0f} s")
