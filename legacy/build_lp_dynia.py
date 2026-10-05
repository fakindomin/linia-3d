"""Lowpoly dynia 100 x 100 x 65 mm (jak build_pumpkin.py): korpus z 16 plytkimi platami, korpus z 12 glebokimi platami, ogonek na czop 5x5x8.
 lp_dynia_korpus.stl, lp_dynia_korpus_platy.stl, lp_dynia_ogonek.stl (druk do gory nogami: koniec ogonka na stole)"""
import sys, time, pickle
import numpy as np
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
import build_pumpkin as BP

T0 = time.time()
N_SM, AMP_SM = 16, 1.25  # korpus: 16 plytkich platow (rowek 2,5 mm); 32 wierzcholki na pierscien, grzbiety co 22,5 st. (na osiach x, y)
N_LB, AMP_LB = 12, 2.5   # korpus_platy: 12 glebokich platow (rowek 5 mm); rowki zanikaja ku zaglebieniu
S_SM = S_LB = BP.make_shape(0.0)      # grzbiety 50,0 -> szerokosc 100 mm
H_TOP, ZC = BP.H_TOP, BP.ZC
ZS_LOW = [0.0, 4.5, 10.0, 17.0, 25.0, 32.0]
ZS_UP = [39.0, 46.0, 52.0, 57.0, 60.5, 63.0]


def profile(S):
    rings = [(z, float(BP.R_mean(z, S))) for z in ZS_LOW + ZS_UP + [H_TOP]]
    for rho in (12.0, 8.0, 4.0):                         # zaglebienie na ogonek (jak top_surface)
        rings.append((float(BP.top_surface(rho)), rho))
    return rings


def revolve_lobed(rings, N, amp):
    """bryla z N platami: pierscienie 2N-katne (grzbiet / rowek), wszystkie w tej samej fazie (pionowe grzbiety);
    przekatne scian symetryczne (jodelka) wzgledem grzbietow i rowkow"""
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


solid_sm = revolve_lobed(profile(S_SM), N_SM, AMP_SM)
solid_lb = revolve_lobed(profile(S_LB), N_LB, AMP_LB)
for nm, m in (("16 platow", solid_sm), ("12 platow", solid_lb)):
    print(f"{nm}: {len(m.faces)} tr, wt {m.is_watertight}, ext {m.extents.round(2).tolist()}, obj. {m.volume / 1000:.1f} cm3")

P_STEM = np.array([0.0, 0.0, top_z_at(solid_sm, 0.0, 0.0)])
assert abs(P_STEM[2] - top_z_at(solid_lb, 0.0, 0.0)) < 1e-6
FR_STEM = socket_frame(P_STEM, B=(0, 0, 1), A=(1, 0, 0), C=(0, -1, 0))
print(f"dno zaglebienia z = {P_STEM[2]:.2f}")
sock = to_global(socket_solid(), FR_STEM)
body_sm, body_lb = diff(solid_sm, sock), diff(solid_lb, sock)
save_lp(body_sm, "lp_dynia_korpus.stl", upright=True, note="16 plytkich platow; gniazdo na ogonek w zaglebieniu")
save_lp(body_lb, "lp_dynia_korpus_platy.stl", upright=True, note="12 glebokich platow; gniazdo na ogonek")

# ---------- ogonek ----------
STEM_H, STEM_R0, STEM_RT, BEND, M_S = BP.STEM_H, BP.STEM_R0, BP.STEM_RT, BP.BEND, 8


def stem_solid():
    r = lambda b: STEM_RT + (STEM_R0 - STEM_RT) * (1 - float(np.clip(b / STEM_H, 0, 1))) ** 3
    bs = [-3.0, 0.0, 3.3, 6.6, 11.0, 15.4, STEM_H]
    m = revolve_rings([(b, r(b)) for b in bs], M_S)
    V = m.vertices.copy()
    t = np.clip(V[:, 2] / STEM_H, 0, 1)
    loc = np.c_[V[:, 0] + BEND * t * t, V[:, 2], 2.5 - V[:, 1]]          # (a, b, c) = (x + zgiecie, z, 2,5 - y)
    g = trimesh.Trimesh(loc, m.faces.copy(), process=False)
    trimesh.repair.fix_normals(g)
    if g.volume < 0:
        g.invert()
    return g


stem = stem_solid()
o_sm, o_lb = offset(solid_sm, GAP_), offset(solid_lb, GAP_)
st = diff(stem, to_local(o_sm, FR_STEM), to_local(o_lb, FR_STEM))
comps = st.split(only_watertight=False)
if len(comps) > 1:
    comps.sort(key=lambda c: -abs(c.volume))
    print("   skladowe ogonka po przycieciu:", [round(abs(c.volume), 1) for c in comps]); st = comps[0]
st = union(st, peg_solid(1.0))
# druk do gory nogami: (a, b, c) -> (a, c, -b): koniec ogonka na stole, czop do gory
Rm = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
st_p = st.copy(); st_p.apply_transform(Rm)
save_lp(st_p, "lp_dynia_ogonek.stl", upright=True, note="druk do gory nogami: koniec ogonka na stole, czop 5x5 sterczy do gory")
pickle.dump(dict(FR_STEM=FR_STEM, P_STEM=P_STEM, stem_local=st, body_sm=body_sm, body_lb=body_lb, solid_sm=solid_sm, solid_lb=solid_lb),
            open(OUT + "/_lp_dynia.pkl", "wb"))
print(f"czas {time.time() - T0:.0f} s")
