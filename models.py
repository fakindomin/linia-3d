"""DANE modeli (idealne obrysy i porty) + budowniczowie lowpoly dla 5 modeli kluczowych: krolik/renifer, jajko, dynia, balwan.
Wzor dla nowych modeli: new_model_template.py. Profile ideale definiuja pliki zrodlowe stylu zebrowanego (shapes.py, build_pumpkin.py,
build_snowman.py) - tu sa tylko podpiete (jedna definicja profilu na model, ten sam dla zeber i lowpoly)."""
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standard import *
import shapes as SH
import build_pumpkin as BP
import build_snowman as BS

# =====================================================================================================
# KROLIK / RENIFER (korpus bazowy 121 mm, uszy / poroza na gniazdach w glowie)
# =====================================================================================================
Rb = lambda z: float(SH.bunny_profile(np.float64(z)))
BUNNY = Model("krolik", outline_R(Rb, 0.0, 121.0), ports=ear_ports(Rb, 105.0, 121.0), ribbed_F=SH.bunny_F)
BUNNY.Rfun = Rb
BUNNY.zport = BUNNY.ports["ear_R"].P0[2]

# =====================================================================================================
# JAJKO NIESPODZIANKA (miseczka 0..34 + czapka 34,2..89,5; uszy / poroza w czapce)
# =====================================================================================================
Re = lambda z: float(SH.egg_R(np.float64(z)))
EGG = Model("jajko", outline_R(Re, 0.0, SH.H_EGG), ports=ear_ports(Re, SH.ZM, SH.H_EGG), ribbed_F=SH.egg_F)
EGG.Rfun = Re
EGG.zport = EGG.ports["ear_R"].P0[2]

# =====================================================================================================
# DYNIA 100 x 100 x 65 (ogonek na czopie w zaglebieniu); obrys = grzbiety (promien szczytu platow)
# =====================================================================================================
S_PUMP = BP.make_shape(0.0)                      # a = 50 -> szerokosc 100 mm
Rp = lambda z: float(BP.R_mean(np.float64(z), S_PUMP))
P_DIP_Z = BP.H_TOP - BP.DIP                      # 59,0: dno zaglebienia (P0 ogonka)


def _pump_outline():
    side = [(max(Rp(z), 0.0), z) for z in np.arange(0.0, BP.H_TOP, 0.2)] + [(Rp(BP.H_TOP), BP.H_TOP)]
    dip = [(rho, float(BP.top_surface(rho))) for rho in np.linspace(BP.R_SH, 0.0, 80)]
    return np.array([(0.0, 0.0)] + side + dip)


PUMPKIN = Model("dynia", _pump_outline(), pad=1.8, ribbed_F=lambda X, Y, Z: BP.pumpkin_F(X, Y, Z, BP.S_FINE, "fine"))    # pad 1,8 = amplituda wariantu 36 platow
PUMPKIN.ports = {"stem": Port("stem", (0, 0, P_DIP_Z), socket_frame((0, 0, P_DIP_Z), B=(0, 0, 1), A=(1, 0, 0), C=(0, -1, 0)), "stem")}
PUMPKIN.Rfun = Rp
PUMPKIN.zport = P_DIP_Z

# =====================================================================================================
# BALWAN 150 mm (3 kule + kapelusz; nos z przodu, miotla 55 st. na prawo)
# =====================================================================================================
Rs = lambda z: float(BS.R_prof(np.float64(z)))
SNOWMAN = Model("balwan", outline_R(Rs, 0.0, BS.TOTAL, steps=(BS.ZT,)),
                ports={"nose": Port("nose", BS.P_NOSE, BS.FR_NOSE, "nose"), "broom": Port("broom", BS.P_BROOM, BS.FR_BROOM, "broom")},
                ribbed_F=BS.snow_F)
SNOWMAN.Rfun = Rs

MODELS = {m.name: m for m in (BUNNY, EGG, PUMPKIN, SNOWMAN)}


# =====================================================================================================
# LOWPOLY: budowniczowie (uzywaja WYLACZNIE standard.py + lp_parts.py)
# =====================================================================================================
from lp_parts import ear_leaf, antler_solid, mirror_a, path_rings

SIDES = ((+1, "prawe", "ear_R"), (-1, "lewe", "ear_L"))
L_LONG = 42.0                                    # dlugie ucho (widoczna dlugosc)


def ear_length_short():
    """krotkie ucho: czubek na z = 150 (jak w zebrowanym), L = (150 - z_P0) / cos 14"""
    return (TOTAL_H - BUNNY.zport) / math.cos(TILT)


# ---------- krolik / renifer ----------
def lp_bunny_solid():
    rings = lp_section_rings(BUNNY.Rfun, 0.0, 121.0, port_zs=[BUNNY.zport], apex_top=True)
    return lp_revolve([rings])


def antler_lam():
    fr = BUNNY.ports["ear_R"].frame
    lo, hi = 0.9, 1.15
    for _ in range(30):
        mid = (lo + hi) / 2
        top = to_global(antler_solid(mid), fr).bounds[1][2]
        lo, hi = (mid, hi) if top < TOTAL_H else (lo, mid)
    return (lo + hi) / 2


def lp_ear_parts():
    """uszy (krotkie, dlugie) i poroza: przyciete do kopert krolika i jajka, czop 5x5x8; zwraca {nazwa: mesh}"""
    Ls, lam = ear_length_short(), antler_lam()
    leaf_s, leaf_l, ant_R = ear_leaf(Ls, -3.0), ear_leaf(L_LONG, -3.0), antler_solid(lam)
    ant_L = mirror_a(ant_R)
    out = {}
    for s, nm, pn in SIDES:
        tg = [(BUNNY, pn), (EGG, pn)]
        out[f"lp_ucho_{nm}"] = lp_trim(leaf_s, tg)
        out[f"lp_ucho_dlugie_{nm}"] = lp_trim(leaf_l, tg)
        out[f"lp_poroze_{nm}"] = lp_trim(ant_R if s > 0 else ant_L, tg)
    return out, dict(L_SHORT=Ls, LAM=lam)


# ---------- jajko ----------
M_E, ZL, Z_CAP0 = 14, 41.0, 34.2
R_CAV, R_LIP, R_BORE, FLOOR, CEIL, R_TOP, WALL_CAP, CONE = 24.0, 25.2, 25.45, 4.5, 76.0, 5.0, 3.0, LP_SLOPE
EGG_LOW = [0.0, 3.5, 8.0, 14.0, 21.0, 28.0, 34.0]
EGG_UP = [34.2, 40.0, 46.0, 52.0, 58.0, 64.0, 70.0, 75.0, 79.0, 83.0, 86.0, 88.5]


def _er(zs):
    return [(z, Re(z)) for z in zs]


def lp_egg_outer(kind):
    if kind == "cup":
        return revolve_rings(_er(EGG_LOW), M_E)
    if kind == "cap":
        return revolve_rings(_er(EGG_UP) + [(SH.H_EGG, 0.0)], M_E, j0=(len(EGG_LOW) - 1) % 2)
    zr = _er(EGG_LOW) + [(EGG_UP[0], Re(EGG_UP[0]), "same")] + _er(EGG_UP[1:]) + [(SH.H_EGG, 0.0)]
    return revolve_rings(zr, M_E)


def lp_egg_parts():
    cup_out, cap_out = lp_egg_outer("cup"), lp_egg_outer("cap")
    rc = lambda z: min(Re(z) - SH.WALL_CUP, R_CAV)
    zr = [(FLOOR, rc(FLOOR)), (9.0, rc(9.0)), (15.0, rc(15.0)), (24.0, R_CAV, 0), (30.0, R_CAV, "same"), (ZL + 1.0, R_CAV, "same")]
    cav_cup = revolve_rings(zr, M_E)
    cup = diff(union(cup_out, prism(M_E, R_LIP, 34.0 - 1.0, ZL)), cav_cup)
    bore = prism(M_E, R_BORE, Z_CAP0 - 0.8, ZL + 0.5)
    za = CEIL - (R_CAV - R_TOP) / CONE
    zr = [(ZL, R_CAV, 0), (47.0, R_CAV, "same")]
    for z in (53.0, 59.0, 63.0, 67.0, 71.0, 74.0):
        zr.append((z, min(Re(z) - WALL_CAP, R_CAV - max(z - za, 0.0) * CONE)))
    zr.append((CEIL, R_TOP))
    cav_body = revolve_rings(zr, M_E)
    cap_core = diff(cap_out, bore, cav_body)
    out = {"lp_jajko_miseczka": cup, "lp_jajko_czapka_gniazda": cut_ports(cap_core, EGG)}
    Ls = ear_length_short()
    for nm, L in (("lp_jajko_czapka_uszy", Ls), ("lp_jajko_czapka_uszy_dlugie", L_LONG)):
        leaf = ear_leaf(L, -4.5)
        out[nm] = diff(union(cap_out, *[to_global(leaf, EGG.ports[pn].frame) for _, _, pn in SIDES]), bore, cav_body)
    return out, dict(cup_out=cup_out, cap_out=cap_out, full=lp_egg_outer("full"))


# ---------- dynia ----------
N_SM, AMP_SM = 16, 1.25
N_LB, AMP_LB = 12, 2.5
ZS_LOW = [0.0, 4.5, 10.0, 17.0, 25.0, 32.0]
ZS_UP = [39.0, 46.0, 52.0, 57.0, 60.5, 63.0]
DIP_RINGS = (12.0, 8.0)                           # zaglebienie: pierscienie wg idealnej krzywej; dno plaskie z = 59,0, r = 2,5
DIP_FLOOR_R = 2.5


def pump_profile():
    rings = [(z, Rp(z)) for z in ZS_LOW + ZS_UP + [BP.H_TOP]]
    rings += [(float(BP.top_surface(rho)), rho) for rho in DIP_RINGS]
    rings.append((P_DIP_Z, DIP_FLOOR_R))
    return rings


def revolve_lobed(rings, N, amp):
    """N platow: pierscienie 2N-katne (grzbiet r / rowek r - d), pionowe grzbiety, jodelka; d = 2 amp, zanika dla r < 28 (zaglebienie gladkie)"""
    V, idx = [], []
    for z, r in rings:
        d = 2 * amp * float(np.clip((r - 12.0) / 16.0, 0, 1))
        ring = []
        for k in range(2 * N):
            rr = r if k % 2 == 0 else r - d
            a = math.pi * k / N
            V.append((rr * math.cos(a), rr * math.sin(a), z)); ring.append(len(V) - 1)
        idx.append(ring)
    K, F = 2 * N, []
    for j in range(len(rings) - 1):
        A, B = idx[j], idx[j + 1]
        for k in range(K):
            k1 = (k + 1) % K
            if k % 2 == 0:
                F += [(A[k], A[k1], B[k1]), (A[k], B[k1], B[k])]
            else:
                F += [(A[k], A[k1], B[k]), (A[k1], B[k1], B[k])]
    for ring, top in ((idx[0], False), (idx[-1], True)):
        V.append((0.0, 0.0, V[ring[0]][2])); c = len(V) - 1
        for k in range(K):
            F.append((c, ring[k], ring[(k + 1) % K]) if top else (c, ring[(k + 1) % K], ring[k]))
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    m.merge_vertices()
    trimesh.repair.fix_normals(m)
    if m.volume < 0:
        m.invert()
    return m


STEM_H, STEM_R0, STEM_RT, BEND, M_S = BP.STEM_H, BP.STEM_R0, BP.STEM_RT, BP.BEND, 8


def lp_stem_solid():
    r = lambda b: STEM_RT + (STEM_R0 - STEM_RT) * (1 - float(np.clip(b / STEM_H, 0, 1))) ** 3
    bs = [-3.0, 0.0, 3.3, 6.6, 11.0, 15.4, STEM_H]
    m = revolve_rings([(b, r(b)) for b in bs], M_S)
    V = m.vertices.copy()
    t = np.clip(V[:, 2] / STEM_H, 0, 1)
    g = trimesh.Trimesh(np.c_[V[:, 0] + BEND * t * t, V[:, 2], 2.5 - V[:, 1]], m.faces.copy(), process=False)
    trimesh.repair.fix_normals(g)
    if g.volume < 0:
        g.invert()
    return g


def lp_pumpkin_parts():
    sm, lb = revolve_lobed(pump_profile(), N_SM, AMP_SM), revolve_lobed(pump_profile(), N_LB, AMP_LB)
    p = PUMPKIN.ports["stem"]
    stem = lp_trim(lp_stem_solid(), [(PUMPKIN, "stem")], ext=1.0)
    Rm = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)      # druk do gory nogami: (a,b,c) -> (a,c,-b)
    st_p = stem.copy(); st_p.apply_transform(Rm)
    return {"lp_dynia_korpus": cut_ports(sm, PUMPKIN), "lp_dynia_korpus_platy": cut_ports(lb, PUMPKIN), "lp_dynia_ogonek": st_p}, dict(sm=sm, lb=lb, stem_local=stem)


# ---------- balwan ----------
def _kink_head_brim():
    zz = np.arange(100.0, 106.0, 0.02)
    r = np.array([Rs(z) for z in zz])
    return float(zz[np.argmin(r)])


def snowman_sections():
    Zk = _kink_head_brim()
    R1, _ = clamp_overhang(Rs, 0.0)
    ZW1 = 47.15
    zb = SNOWMAN.ports["broom"].P0[2]
    zn = SNOWMAN.ports["nose"].P0[2]
    Rhat = lambda z: Rs(max(z, BS.ZT + 1e-3))
    s1 = lp_section_rings(R1, 0.0, ZW1, M=14, forced=[ZW1])                                   # kula 1 (R 27,2 -> M 14)
    s2 = lp_section_rings(Rs, ZW1 + 0.8, zb, M=10, port_zs=[zb], port_ang=0.0)                # kula 2 (R 21,5 -> M 10), port miotly na +x
    s3 = lp_section_rings(Rs, zb + 1.5, BS.ZT, M=10, forced=[Zk, BS.ZT - 2.5, BS.ZT - 0.6], port_zs=[zn], port_ang=270.0)   # glowa + rondo (R 20 -> M 10), port nosa na -y
    s4 = [ring_regular(BS.ZT, BS.RC, 8, half=0)] + lp_section_rings(Rhat, BS.ZT + 1e-3, BS.TOTAL, M=8, forced=[BS.TOTAL - BS.FIL])[1:]   # cylinder kapelusza (M 8)
    return [s1, s2, s3, s4]


def lp_snowman_solid():
    return lp_revolve(snowman_sections())


# nos: marchewka (stozek 7-kat, plaski spod c = 0), miotla: raczka + glowica z wycieciami
def lp_nose_solid():
    L, r0, rt = BS.NOSE_L, BS.NOSE_R0, BS.NOSE_RT
    ang = np.radians([-44.4, 0, 45, 90, 135, 180, 224.4])
    ring = lambda b, r: [(r * math.cos(t), b, 0.7 * r + r * math.sin(t)) for t in ang]
    rings = [ring(-3.0, r0), ring(0.0, r0), ring(L * 0.5, (r0 + rt) / 2), ring(L, rt)]
    return loft(rings, apex=None)


def lp_broom_solid():
    T, w = ANT_T, 4.4
    base = pillow_box(-3.4, 3.4, -3.0, 4.0, T, 1.0, 1.2)
    handle = path_rings([(0.0, -3.0), (0.0, BS.BR_HANDLE + 2)], w, 0.8, T, tip=0.0)
    ring = lambda b, hw: [(-hw, b, 0.0), (hw, b, 0.0), (hw, b, 1.0), (max(hw - 2.6, 0.35 * hw), b, T), (-max(hw - 2.6, 0.35 * hw), b, T), (-hw, b, 1.0)]
    head = loft([ring(BS.BR_HANDLE - 1, 3.6), ring((BS.BR_HANDLE + BS.BR_TOTAL) / 2, 6.1), ring(BS.BR_TOTAL, 8.6)], apex=None)
    m = union(base, handle, head)
    for ax in (-5.1, -1.7, 1.7, 5.1):                     # V-wyciecia miedzy pekami (glebokosc 6,5 mm, szerokosc 2,0 mm)
        a0 = ax * 0.55
        tri = lambda c: [(a0 - 1.0, BS.BR_TOTAL + 1, c), (a0 + 1.0, BS.BR_TOTAL + 1, c), (a0, BS.BR_TOTAL - 6.5, c)]
        m = diff(m, loft([tri(-1.0), tri(T + 1.0)], apex=None))
    return m


def lp_snowman_parts():
    body = lp_snowman_solid()
    nose = lp_trim(lp_nose_solid(), [(SNOWMAN, "nose")], ext=1.0)
    broom = lp_trim(lp_broom_solid(), [(SNOWMAN, "broom")], ext=1.0)
    return {"lp_balwan": cut_ports(body, SNOWMAN), "lp_balwan_nos": nose, "lp_balwan_miotla": broom}, dict(solid=body)
