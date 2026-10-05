"""Zgodnosc krzyzowa zebrowane <-> lowpoly: czesci wymienne jednego stylu na korpusach drugiego (te same pozycje gniazd x=+-6, 14 st.; dynia: gniazdo w zaglebieniu)"""
import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
import shapes as SH
from parts import mount_frame
from scipy.spatial import cKDTree
LP = pickle.load(open(OUT + "/_lp_frames.pkl", "rb")); DY = pickle.load(open(OUT + "/_lp_dynia.pkl", "rb")); EG = pickle.load(open(OUT + "/_lp_egg.pkl", "rb"))
L = lambda n: trimesh.load(OUT + f"/{n}.stl")

def fit(part_local, frame, body_with_sockets, label):
    g = to_global(part_local, frame)
    a, b, c = frame.to_local(*g.vertices.T)
    pts, _ = trimesh.sample.sample_surface(body_with_sockets, 500000, seed=1); T = cKDTree(pts)
    d, _ = T.query(g.vertices)
    ov = abs(inter(g, body_with_sockets).volume)
    print(f"  {label:44s} wspolna obj. {ov:7.2f} mm3 | czop-gniazdo {d[b < -0.5].min():.2f} | podstawa {d[b > 0.4].min():.2f} mm | czubek z={g.bounds[1][2]:.1f}")

# ---- korpusy z gniazdami
rib_body = L("korpus_bazowy"); lp_body = L("lp_korpus_bazowy")
FRb_rib = {s: mount_frame(s, SH.bunny_P0(s)) for s in (1, -1)}; FRb_lp = LP["FRb"]
FRe_rib = {s: mount_frame(s, SH.egg_P0(s)) for s in (1, -1)}; FRe_lp = LP["FRe"]
cap_rib = L("jajko_czapka_gniazda"); cap_rib.apply_translation([0, 0, 34.2]); cap_lp = EG["cap_sock"]
parts_rib = {"ucho": L("ucho_prawe"), "ucho_dlugie": L("ucho_dlugie_prawe"), "poroze": L("poroze_prawe")}
parts_lp = {"ucho": L("lp_ucho_prawe"), "ucho_dlugie": L("lp_ucho_dlugie_prawe"), "poroze": L("lp_poroze_prawe")}
print("== KROLIK/RENIFER: czesci ZEBROWANE na korpusie LOWPOLY"); [fit(p, FRb_lp[1], lp_body, f"{n} (zebr.) -> lp korpus") for n, p in parts_rib.items()]
print("== KROLIK/RENIFER: czesci LOWPOLY na korpusie ZEBROWANYM"); [fit(p, FRb_rib[1], rib_body, f"{n} (lp) -> zebr. korpus") for n, p in parts_lp.items()]
print("== JAJKO: czesci ZEBROWANE na czapce LOWPOLY"); [fit(p, FRe_lp[1], cap_lp, f"{n} (zebr.) -> lp czapka") for n, p in parts_rib.items()]
print("== JAJKO: czesci LOWPOLY na czapce ZEBROWANEJ"); [fit(p, FRe_rib[1], cap_rib, f"{n} (lp) -> zebr. czapka") for n, p in parts_lp.items()]
# ---- dynia: ogonek
from lib import socket_frame
FR_lp = DY["FR_STEM"]; FR_rib = socket_frame(np.array([0.0, 0.0, 59.0]), B=(0, 0, 1), A=(1, 0, 0), C=(0, -1, 0))
Rm = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
def stem_local(m):
    g = m.copy(); g.apply_translation([0, 0, -22.0]); g.apply_transform(np.linalg.inv(Rm)); return g
st_rib = stem_local(L("dynia_ogonek")); st_lp = DY["stem_local"]
print("== DYNIA"); 
fit(st_rib, FR_lp, DY["body_sm"], "ogonek (zebr.) -> lp dynia 16 platow"); fit(st_rib, FR_lp, DY["body_lb"], "ogonek (zebr.) -> lp dynia 12 platow")
fit(st_lp, FR_rib, L("dynia_korpus"), "ogonek (lp) -> zebr. dynia drobna"); fit(st_lp, FR_rib, L("dynia_korpus_platy"), "ogonek (lp) -> zebr. dynia platy")
