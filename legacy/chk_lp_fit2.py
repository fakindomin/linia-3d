import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from scipy.spatial import cKDTree
P = pickle.load(open(OUT + "/_lp_frames.pkl", "rb")); FRb = P["FRb"]
body_s = trimesh.load(OUT + "/lp_korpus_bazowy.stl")
pts, _ = trimesh.sample.sample_surface(body_s, 600000, seed=1); T = cKDTree(pts)
for nm in ["ucho_prawe", "ucho_dlugie_lewe", "poroze_prawe", "poroze_lewe"]:
    m = trimesh.load(OUT + f"/lp_{nm}.stl"); s = +1 if "prawe" in nm else -1
    g = to_global(m, FRb[s]); a, b, c = FRb[s].to_local(*g.vertices.T)
    d, _ = T.query(g.vertices)
    ov = abs(inter(g, body_s).volume)
    print(f"{nm:18s}: czop-gniazdo min odl. {d[b < -0.5].min():.2f} | podstawa {d[b > 0.4].min():.2f} | wspolna objetosc z korpusem (gniazda) {ov:.3f} mm3")
