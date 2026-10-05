"""Balwan 150 mm (z kapeluszem) + nos (marchewka) + miotla; zebra ±0,8 mm, rozstaw ~3,4 mm w kazdej kuli osobno."""
import sys, time, math
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from render import render, grid

VOX = 0.35
T0 = time.time()
TOTAL = 150.0
# kule
R1, Z1 = 27.2, 23.7
R2, Z2 = 21.5, 63.34
R3, Z3 = 16.5, 93.34
P_SM = 14.0
ZW1, ZW2 = 47.0, 81.5                 # polozenie "talii" (przeciecie kul)
# kapelusz
ZT, RB, RC = 111.83, 20.0, 12.5       # gorna plaszczyzna ronda, promien ronda, promien cylindra
FIL = 1.5
N1, N2, N3, NH = 52, 42, 32, 24       # liczba zeber (rozstaw ok. 3,4 mm w kazdej czesci)


def ball(z, zc, R):
    d = (z - zc) / R
    return R * np.sqrt(np.clip(1 - d * d, 0, None))


def hat_r(z):
    r = np.zeros_like(z)
    r = np.where((z >= ZT - 2.5 - RB) & (z < ZT - 2.5), RB - (ZT - 2.5 - z), r)       # spod ronda: stozek 45 st.
    r = np.where((z >= ZT - 2.5) & (z <= ZT - 0.6), RB, r)
    r = np.where((z > ZT - 0.6) & (z <= ZT), RB - (z - (ZT - 0.6)), r)                  # faza gornej krawedzi ronda
    r = np.where((z > ZT) & (z <= TOTAL - FIL), RC, r)
    r = np.where((z > TOTAL - FIL) & (z <= TOTAL),
                 RC - FIL + np.sqrt(np.clip(FIL ** 2 - (z - (TOTAL - FIL)) ** 2, 0, None)), r)
    return r


def R_prof(z):
    z = np.asarray(z, np.float32)
    rb = (ball(z, Z1, R1) ** P_SM + ball(z, Z2, R2) ** P_SM + ball(z, Z3, R3) ** P_SM) ** (1 / P_SM)
    return np.maximum(rb, hat_r(z))


def sstep(z, z0, z1):
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    return t * t * (3 - 2 * t)


def snow_F(X, Y, Z):
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    R = R_prof(Z)
    w1 = 1 - sstep(Z, ZW1 - 5.5, ZW1 - 3.5)
    w2 = sstep(Z, ZW1 + 3.5, ZW1 + 5.5) * (1 - sstep(Z, ZW2 - 5.5, ZW2 - 3.5))
    w3 = sstep(Z, ZW2 + 3.5, ZW2 + 5.5) * (1 - sstep(Z, 97.0, 99.5))
    wh = sstep(Z, ZT + 6.0, ZT + 8.0) * (1 - sstep(Z, TOTAL - FIL - 2.0, TOTAL - FIL))

    def rib(N):
        c = np.cos(N * th)
        return np.sign(c) * np.abs(c) ** 0.8
    amp = rib_amp(R)
    mod = amp * (w1 * rib(N1) + w2 * rib(N2) + w3 * rib(N3) + wh * rib(NH))
    F = (R + mod - 1e-3) - rho
    return np.minimum(np.minimum(F, Z), TOTAL - Z).astype(np.float32)


# ---------- punkty mocowania ----------
Y0 = 0.25
ZN = Z3 - 2.0
RN = math.sqrt(R3 ** 2 - (ZN - Z3) ** 2)
P_NOSE = np.array([0.0, -RN, ZN])                      # nos z przodu (-y), os czopu przez P0
FR_NOSE = socket_frame(P_NOSE, B=(0, -1, 0), A=(-1, 0, 0), C=(0, 0, 1))
ELEV = math.radians(55.0)                              # miotla: 55 st. w gore, na prawo
P_BROOM = np.array([R2 * math.cos(ELEV), Y0, Z2 + R2 * math.sin(ELEV)])
B_BR = np.array([math.cos(ELEV), 0.0, math.sin(ELEV)])
C_BR = np.array([0.0, -1.0, 0.0])
FR_BROOM = socket_frame(P_BROOM, B_BR, np.cross(B_BR, C_BR), C_BR)

def peg1_F(a, b, c):
    return rbox_F(a, b, c, (-PEG_W / 2, -PEG_L, 0.0), (PEG_W / 2, 1.0, PEG_W), PEG_R)


# ---------- nos ----------
NOSE_L, NOSE_R0, NOSE_RT = 22.0, 4.2, 0.9


def nose_fn(sdf, fr):
    def fn(a, b, c):
        r = NOSE_RT + (NOSE_R0 - NOSE_RT) * np.clip(1 - b / NOSE_L, 0, 1)
        cc = 0.7 * r
        d = r - np.sqrt(a ** 2 + (c - cc) ** 2)
        F = np.minimum(np.minimum(d, NOSE_L - b), np.minimum(c, b + 3.0))
        if sdf is not None:
            X = fr.O[0] + a * fr.A[0] + b * fr.B[0] + c * fr.C[0]
            Y = fr.O[1] + a * fr.A[1] + b * fr.B[1] + c * fr.C[1]
            Z = fr.O[2] + a * fr.A[2] + b * fr.B[2] + c * fr.C[2]
            F = np.minimum(F, -(sdf(X, Y, Z) + GAP))
        return np.maximum(F, peg1_F(a, b, c)).astype(np.float32)
    return fn


# ---------- miotla ----------
BR_HANDLE, BR_TOTAL = 38.0, 58.0


def broom_flat(res=0.1):
    cv = Canvas(-12, 12, -4.5, BR_TOTAL + 2, res=res)
    cv.path([(0, -3.0), (0, BR_HANDLE + 2)], 4.4)
    cv.rect(-3.4, 3.4, -3.0, 4.0)                                    # podstawa pod czop
    cv.poly([(-3.6, BR_HANDLE - 1), (3.6, BR_HANDLE - 1), (8.6, BR_TOTAL), (-8.6, BR_TOTAL)])   # glowica (wachlarz)
    for ax in (-5.1, -1.7, 1.7, 5.1):                                  # wyciecia miedzy pekami
        t = ax / 8.6
        cv.poly([(ax * 0.55 - 0.6, BR_TOTAL + 1), (ax * 0.55 + 0.6, BR_TOTAL + 1), (ax * 0.55, BR_TOTAL - 5.5)], 0)
    cv.close_(1.0)
    gr = Canvas(-12, 12, -4.5, BR_TOTAL + 2, res=res)
    gr.line((-3.0, BR_HANDLE + 3.0), (3.0, BR_HANDLE + 3.0), 1.2)        # wiazanie
    for ax in (-3.4, 0.0, 3.4):                                          # rowki pekow
        gr.line((ax * 0.62, BR_HANDLE + 6.0), (ax * 0.98, BR_TOTAL - 6.5), 0.9)
    return FlatPart(cv, ANT_T, w=1.0, k=2.2, groove_mask=gr.mask(), groove_d=0.9)


def build_all():
    x_h = 30.0
    axes, (X, Y, Z) = make_grid(-x_h, x_h, -x_h, x_h, -1.0, TOTAL + 1.5, VOX)
    F0 = snow_F(X, Y, Z)
    F = F0.copy()
    for fr in (FR_NOSE, FR_BROOM):
        a, b, c = fr.to_local(X, Y, Z)
        F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
    return axes, F0, F


if __name__ == "__main__":
    print(f"nos P0={P_NOSE.round(2)}  miotla P0={P_BROOM.round(2)}")
    axes, F0, F = build_all()
    body = mesh_from_F(F, axes, VOX)
    print("bryla:", len(body.faces), "tr.", body.is_watertight, body.extents)
    body = decimate(body, 240000, label="balwan")
    save(body, "balwan.stl", True, "kapelusz w calosci; 2 gniazda: nos (przod) i miotla (prawa strona)")
    from models import SNOWMAN                       # STANDARD v1.0: przycinanie do koperty (zebra i lowpoly)
    sdf_nose = sdf_broom = SNOWMAN.env.sdf
    nose = local_mesh(nose_fn(sdf_nose, FR_NOSE), (-6, 6), (-9, NOSE_L + 1), (-0.6, 9.5), 0.2)
    save(nose, "balwan_nos.stl", False, "marchewka: plaski spod na stole, bez podpor")
    bf = broom_flat()
    def broom_fn(a, b, c):
        F_ = np.minimum(bf.F(a, b, c), b + 3.0)
        X_ = FR_BROOM.O[0] + a * FR_BROOM.A[0] + b * FR_BROOM.B[0] + c * FR_BROOM.C[0]
        Y_ = FR_BROOM.O[1] + a * FR_BROOM.A[1] + b * FR_BROOM.B[1] + c * FR_BROOM.C[1]
        Z_ = FR_BROOM.O[2] + a * FR_BROOM.A[2] + b * FR_BROOM.B[2] + c * FR_BROOM.C[2]
        F_ = np.minimum(F_, -(sdf_broom(X_, Y_, Z_) + GAP))
        return np.maximum(F_, peg1_F(a, b, c)).astype(np.float32)
    broom = local_mesh(broom_fn, (-12, 12), (-9, BR_TOTAL + 1), (-0.6, 7.0), 0.2)
    save(broom, "balwan_miotla.stl", False, "druk na plasko; na wlasne gniazdo 55 st.")

    # --- pasowanie ---
    tree = surf_tree(body, 600000)
    for nm, m, fr in (("nos", nose, FR_NOSE), ("miotla", broom, FR_BROOM)):
        g = to_global(m, fr)
        dd, _ = tree.query(g.vertices)
        a_, b_, c_ = fr.to_local(*g.vertices.T)
        V = g.vertices
        Fv = snow_F(V[:, 0], V[:, 1], V[:, 2])
        a2, b2, c2 = fr.to_local(V[:, 0], V[:, 1], V[:, 2])
        Fv = np.minimum(Fv, -socket_F(a2, b2, c2))
        print(f"{nm}: podstawa {dd[b_ > 0.4].min():.2f} | czop {dd[b_ < -0.5].min():.2f} mm | w korpusie {int((Fv > 0.02).sum())} | "
              f"zasieg x {V[:, 0].min():.1f}..{V[:, 0].max():.1f}, z max {V[:, 2].max():.1f}")
    ims = [render([body], 0, 6, 520, 900, ext=900 / 165, center=(0, 75)),
           render([body, to_global(nose, FR_NOSE), to_global(broom, FR_BROOM)], 0, 6, 700, 900, ext=900 / 165, center=(15, 75)),
           render([body, to_global(nose, FR_NOSE), to_global(broom, FR_BROOM)], -70, 6, 700, 900, ext=900 / 165, center=(15, 75))]
    grid(ims, 3).save(OUT + "/podglad_balwan.png")
    json.dump(REPORT, open(OUT + "/_raport.json", "w"), indent=1, ensure_ascii=False)
    print(f"czas {time.time() - T0:.0f} s")
