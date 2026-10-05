"""Dynia 100 x 100 x 65 mm: wariant z drobnymi zebrami (jak cala linia) i wariant z szerokimi platami (36) + ogonek na czop."""
import sys, time, math
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from render import render, grid, section_img

VOX = 0.4
T0 = time.time()
H_TOP, R_BASE = 65.0, 32.0            # wysokosc ramienia dyni, promien plaskiej podstawy (O 64)
R_SH = 16.0                           # promien ramienia (wokol zaglebienia)
DIP = 6.0                             # glebokosc zaglebienia na ogonek
ZC = 32.0
P_STEM = np.array([0.0, 0.0, H_TOP - DIP])
FR_STEM = socket_frame(P_STEM, B=(0, 0, 1), A=(1, 0, 0), C=(0, -1, 0))


def make_shape(amp_total, n_u=2.2):
    """parametry elipsoidy (srednia, bez zeber), tak by calkowita szerokosc = 100 mm"""
    a = 50.0 - amp_total
    u0 = math.sqrt(1 - (R_BASE / a) ** 2)
    b_l = ZC / u0
    u1 = (1 - (R_SH / a) ** n_u) ** (1 / n_u)
    b_u = (H_TOP - ZC) / u1
    return dict(a=a, b_l=b_l, b_u=b_u, n_u=n_u)


def R_mean(z, S):
    z = np.asarray(z, np.float32)
    ul = np.clip((ZC - z) / S["b_l"], 0, 1)
    uu = np.clip((z - ZC) / S["b_u"], 0, 1)
    low = S["a"] * np.sqrt(np.clip(1 - ul ** 2, 0, None))
    up = S["a"] * np.clip(1 - uu ** S["n_u"], 0, None) ** (1 / S["n_u"])
    return np.where(z <= ZC, low, up)


def top_surface(rho):
    s = np.clip(rho / R_SH, 0, 1)
    return H_TOP - DIP * (1 - s ** 2) ** 1.5


def pumpkin_F(X, Y, Z, S, kind):
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    R = R_mean(Z, S)
    if kind == "fine":
        c = np.cos(92 * th)
        rib = np.sign(c) * np.abs(c) ** 0.8
        amp = RIB_AMP * np.clip((R - 12.0) / 16.0, 0, 1)
    else:
        rib = 2 * np.abs(np.cos(18 * th)) ** 0.55 - 1
        amp = LOBE_A * np.clip((R - 12.0) / 16.0, 0, 1)
    F = (R + amp * rib - 1e-3) - rho
    F = np.minimum(F, np.where(rho < R_SH, top_surface(rho) - Z, 1e3))
    F = np.minimum(F, H_TOP - Z)
    return np.minimum(F, Z).astype(np.float32)


LOBE_A = 1.8
S_FINE = make_shape(RIB_AMP)
S_LOBE = make_shape(LOBE_A)

# ---------- ogonek ----------
STEM_H, STEM_R0, STEM_RT, BEND, STEM_N, STEM_AMP = 22.0, 8.9, 4.4, 5.0, 14, 0.7


def peg1_F(a, b, c):
    return rbox_F(a, b, c, (-PEG_W / 2, -PEG_L, 0.0), (PEG_W / 2, 1.0, PEG_W), PEG_R)


def stem_fn(sdf):
    def fn(a, b, c):
        t = np.clip(b / STEM_H, 0, 1)
        xc = BEND * t * t
        r = STEM_RT + (STEM_R0 - STEM_RT) * (1 - t) ** 3
        y = 2.5 - c
        dx = a - xc
        rho = np.sqrt(dx ** 2 + y ** 2)
        th = np.arctan2(y, dx)
        cs = np.cos(STEM_N * th)
        rib = np.sign(cs) * np.abs(cs) ** 0.8
        F = (r + STEM_AMP * rib - 1e-3) - rho
        F = np.minimum(np.minimum(F, STEM_H - b), b + 3.0)
        if sdf is not None:
            X, Y, Z = a, 2.5 - c, P_STEM[2] + b
            F = np.minimum(F, -(sdf(X, Y, Z) + GAP))
        return np.maximum(F, peg1_F(a, b, c)).astype(np.float32)
    return fn


def body_mesh(S, kind, name, note):
    axes, (X, Y, Z) = make_grid(-52, 52, -52, 52, -1.0, H_TOP + 1.5, VOX)
    F = pumpkin_F(X, Y, Z, S, kind)
    a, b, c = FR_STEM.to_local(X, Y, Z)
    F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
    m = mesh_from_F(F, axes, VOX)
    print(name, "surowa:", len(m.faces), "tr.", m.is_watertight, m.extents.round(2))
    m = decimate(m, 300000, label=name)
    save(m, name, True, note)
    return m


if __name__ == "__main__":
    print("fine:", {k: round(v, 3) if isinstance(v, float) else v for k, v in S_FINE.items()})
    print("lobe:", {k: round(v, 3) if isinstance(v, float) else v for k, v in S_LOBE.items()})
    fine = body_mesh(S_FINE, "fine", "dynia_korpus.stl", "drobne zebra N=92, gniazdo na ogonek w zaglebieniu")
    lobe = body_mesh(S_LOBE, "lobe", "dynia_korpus_platy.stl", "36 szerokich platow, gniazdo na ogonek")
    from models import PUMPKIN                       # STANDARD v1.0: przycinanie do koperty (zebra i lowpoly)
    sdf = PUMPKIN.env.sdf
    stem = local_mesh(stem_fn(sdf), (-12, 12), (-9, STEM_H + 1), (-9, 14), 0.2)
    # druk do gory nogami: czop do gory, koniec ogonka na stole (obrot 180 st. wokol osi a)
    stem_p = stem.copy()
    stem_p.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float))   # z' = -b (koniec ogonka na dole)
    save(stem_p, "dynia_ogonek.stl", True, "druk do gory nogami: koniec ogonka na stole, czop 5x5 sterczy do gory")
    # --- pasowanie ogonka ---
    for nm, body in (("fine", fine), ("platy", lobe)):
        tree = surf_tree(body, 600000)
        g = to_global(stem, FR_STEM)
        dd, _ = tree.query(g.vertices)
        a_, b_, c_ = FR_STEM.to_local(*g.vertices.T)
        V = g.vertices
        Fv = pumpkin_F(V[:, 0], V[:, 1], V[:, 2], S_FINE if nm == "fine" else S_LOBE, "fine" if nm == "fine" else "lobe")
        a2, b2, c2 = FR_STEM.to_local(V[:, 0], V[:, 1], V[:, 2])
        Fv = np.minimum(Fv, -socket_F(a2, b2, c2))
        print(f"ogonek na dyni '{nm}': podstawa {dd[b_ > 0.4].min():.2f} | czop {dd[b_ < -0.5].min():.2f} mm | w korpusie {int((Fv > 0.02).sum())} | "
              f"wierzch z={V[:, 2].max():.1f}")
    st_g = to_global(stem, FR_STEM)
    ims = [render([fine, st_g], 0, 18, 700, 640, ext=640 / 118, center=(0, 38)),
           render([lobe, st_g], 0, 18, 700, 640, ext=640 / 118, center=(0, 38)),
           render([fine, st_g], 0, 60, 700, 640, ext=640 / 118, center=(0, 20)),
           render([stem_p], 0, 12, 360, 640, ext=640 / 40, center=(0, 12))]
    grid(ims, 4).save(OUT + "/podglad_dynia.png")
    json.dump(REPORT, open(OUT + "/_raport.json", "w"), indent=1, ensure_ascii=False)
    print(f"czas {time.time() - T0:.0f} s")
