"""Grupa B - doniczki z podstawkami (S/M/L) i pojemnik z pokrywka (gałka na czop 5x5x8).
 doniczka_S/M/L.stl, podstawka_S/M/L.stl, sloik.stl, sloik_pokrywa.stl (druk gora w dol), sloik_galka.stl"""
import sys, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
from parts import peg_ext_F

T_POT = 3.0
POTS = {  # R_gora, R_dol, H, dno, otwor odpływowy (srednica), zebra N, vox
    "S": dict(Rt=30.0, Rb=22.0, H=55.0, zf=3.5, hole=6.0, N=50, vox=0.35),
    "M": dict(Rt=40.0, Rb=29.0, H=72.0, zf=4.0, hole=8.0, N=64, vox=0.35),
    "L": dict(Rt=50.0, Rb=36.0, H=90.0, zf=4.5, hole=10.0, N=80, vox=0.40),
}
CH = 1.4             # faza dolna 45 st.
COLLAR_H, COLLAR_D, COLLAR_T = 7.5, 1.3, 2.6


def pot_profiles(Rt, Rb, H):
    """(zewn. z kolnierzem, bazowy liniowy do wnetrza)"""
    s = (Rt - Rb) / (H - CH)
    rb = lambda z: Rb + s * (z - CH)
    base_pts = [(0.0, Rb - CH), (CH, Rb), (H, rb(H))]
    Rbase = Prof([(0.0, Rb - CH), (CH, Rb), (H / 2, rb(H / 2)), (H, rb(H))])
    z_c0 = H - COLLAR_H - COLLAR_T
    pts = [(0.0, Rb - CH), (CH, Rb), (H * 0.3, rb(H * 0.3)), (H * 0.6, rb(H * 0.6)), (z_c0, rb(z_c0)),
           (z_c0 + COLLAR_T, rb(z_c0 + COLLAR_T) + COLLAR_D), (H, rb(H) + COLLAR_D)]
    Ro = Prof(with_top_fillet(pts, 1.0))
    return Ro, Rbase


def build_pot(key):
    p = POTS[key]
    Ro, Rbase = pot_profiles(p["Rt"], p["Rb"], p["H"])
    Rin = offset_in(Rbase, T_POT, p["zf"], p["H"], n_ext=2.0)
    name = f"doniczka_{key}"
    check_profile(Ro, Rin, name)
    vox = p["vox"]
    rmax = float(Ro(np.linspace(0, p["H"], 2000)).max())
    axes, (X, Y, Z) = rev_grid(rmax, p["H"] + 1.5, vox)
    F = rev_F(X, Y, Z, Ro, [p["N"]], [], [(p["H"] - COLLAR_H - 1.0, p["H"] + 2)], zlo=0.0, zhi=p["H"])
    F = np.minimum(F, -cav_F(X, Y, Z, Rin, p["zf"]))
    rho = np.sqrt(X ** 2 + Y ** 2)
    F = np.minimum(F, rho - p["hole"] / 2).astype(np.float32)           # otwor odplywowy
    return finish(F, axes, vox, f"{name}.stl", f"otwor odplywowy {p['hole']:.0f} mm; wneka od gory; gladki kolnierz")


def build_saucer(key):
    p = POTS[key]
    Rs = p["Rt"] + COLLAR_D
    Hs = {"S": 9.0, "M": 10.0, "L": 11.0}[key]
    FL = 2.5
    Ro = Prof(with_top_fillet([(0.0, Rs - CH), (CH, Rs), (Hs, Rs)], 1.0))
    Rin = Prof([(FL, Rs - 3.0), (Hs + 2.0, Rs - 3.0)])
    name = f"podstawka_{key}"
    check_profile(Ro, Rin, name)
    vox = p["vox"]
    axes, (X, Y, Z) = rev_grid(Rs + 0.8, Hs + 1.5, vox)
    N = n_ribs(Rs)
    F = rev_F(X, Y, Z, Ro, [N], [], [], zlo=0.0, zhi=Hs)
    F = np.minimum(F, -cav_F(X, Y, Z, Rin, FL))
    rho = np.sqrt(X ** 2 + Y ** 2)
    ri = p["Rb"] + 1.6                                          # luz do doniczki: grzbiety zeber (+0,8) i faza
    ring = np.minimum(np.minimum(ri + 2.2 - rho, rho - ri), np.minimum(FL + 2.2 - Z, Z - (FL - 0.5)))
    F = np.maximum(F, ring).astype(np.float32)
    return finish(F, axes, vox, f"{name}.stl", f"pod doniczke {key}; pierscien centrujacy r {ri:.1f} mm")


# ---------- sloik ----------
RJ, HJ, FJ = 36.0, 74.0, 4.0
NJ = 66
LID_T, LIP_H, LIP_RO, LIP_W = 4.0, 6.0, 33.0 - 0.3, 2.3
BOSS_R, BOSS_H = 9.0, 11.0


def build_jar():
    pts = [(0.0, RJ - CH), (CH, RJ), (HJ, RJ)]
    Ro = Prof(with_top_fillet(pts, 1.0))
    Rin = Prof([(FJ, RJ - 3.0), (HJ + 2.0, RJ - 3.0)])
    check_profile(Ro, Rin, "sloik")
    vox = 0.35
    axes, (X, Y, Z) = rev_grid(RJ + 0.8, HJ + 1.5, vox)
    F = rev_F(X, Y, Z, Ro, [NJ], [], [], zlo=0.0, zhi=HJ)
    F = np.minimum(F, -cav_F(X, Y, Z, Rin, FJ)).astype(np.float32)
    return finish(F, axes, vox, "sloik.stl", "wneka o 66 zebrach; pokrywa wchodzi z luzem 0,3 mm")


def lid_fields():
    vox = 0.35
    axes, (X, Y, Z) = rev_grid(RJ + 0.8, 14.0, vox)
    rho = np.sqrt(X ** 2 + Y ** 2)
    # plyta (zebra), faza 1,2 mm od strony stolu (z = 0 to gorna powierzchnia pokrywy)
    Rp = Prof([(0.0, RJ - 1.2), (1.2, RJ), (LID_T, RJ)])
    F = rev_F(X, Y, Z, Rp, [NJ], [], [], zlo=0.0, zhi=LID_T)
    # kolnierz wchodzacy w sloik (gladki), fazka 0,6 mm na brzegu
    lip = np.minimum(np.minimum(LIP_RO - np.maximum(0.0, Z - (LID_T + LIP_H - 0.6)) - rho, rho - (LIP_RO - LIP_W)),
                     np.minimum(Z - (LID_T - 1.0), (LID_T + LIP_H) - Z))
    # nasada pod gniazdo galki
    boss = np.minimum(BOSS_R - rho, np.minimum(Z - 0.0, BOSS_H - Z))
    F = np.maximum(np.maximum(F, lip), boss)
    # gniazdo 5,4 x 5,4 x 9 od strony stolu (z = 0), os gniazda = os pokrywy
    fr = socket_frame(np.array([0.0, 0.0, 0.0]), B=(0, 0, -1), A=(-1, 0, 0), C=(0, -1, 0))
    a, b, c = fr.to_local(X, Y, Z)
    F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
    return axes, F, vox


def build_lid():
    axes, F, vox = lid_fields()
    return finish(F, axes, vox, "sloik_pokrywa.stl", "druk gora (plaska strona) na stole, kolnierz do gory; gniazdo 5,4x5,4x9 w nasadzie")


KR = 12.0
def build_knob():
    dz, rf = flat_cut_sphere_z(KR, 35.0)
    H = 2 * dz
    zs = np.linspace(0.0, H, 60)
    Rk = Prof([(z, math.sqrt(max(KR ** 2 - (z - dz) ** 2, 0.0))) for z in zs])
    check_profile(Rk, None, "sloik_galka")
    vox = 0.3
    axes, (X, Y, Z) = rev_grid(KR, H + 11.0, vox)
    F = rev_F(X, Y, Z, Rk, [n_ribs(KR)], [], [], zlo=0.0, zhi=H)
    # czop 5x5x8 do gory z plaskiej strony (z = H); ramka: b = -(z - H), c = -y
    fr = Frame(np.array([0.0, 2.5, H]), (-1, 0, 0), (0, 0, -1), (0, -1, 0))
    a, b, c = fr.to_local(X, Y, Z)
    F = np.maximum(F, peg_ext_F(a, b, c)).astype(np.float32)
    return finish(F, axes, vox, "sloik_galka.stl", f"kula R{KR:.0f} ucieta na 35 st. (plaska od stolu); czop 5x5x8 do gory")


if __name__ == "__main__":
    T0 = time.time()
    which = sys.argv[1:] or ["S", "M", "L", "sloik", "lid", "galka"]
    for w in which:
        t = time.time()
        if w in POTS:
            build_pot(w)
            build_saucer(w)
        elif w == "sloik":
            build_jar()
        elif w == "lid":
            build_lid()
        elif w == "galka":
            build_knob()
        print(f"  {w}: {time.time() - t:.0f} s")
    print(f"czas {time.time() - T0:.0f} s")
