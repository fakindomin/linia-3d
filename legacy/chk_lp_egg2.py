import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from scipy.spatial import cKDTree
from trimesh.proximity import thickness, signed_distance
E = pickle.load(open(OUT + "/_lp_egg.pkl", "rb")); P = pickle.load(open(OUT + "/_lp_frames.pkl", "rb")); FRe = P["FRe"]
cup, cap = E["cup"], E["cap_sock"]
# jajko 44 x 68
zz = np.linspace(FLOOR, FLOOR + 68, 400); t = np.clip(np.abs(zz - (FLOOR + 34)) / 34, 0, 1)
rr = 22 * np.clip(1 - t ** 2.3, 0, None) ** (1 / 2.3)
th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
pts = np.array([(r * np.cos(a), r * np.sin(a), z) for z, r in zip(zz, rr) for a in th])
tree = cKDTree(np.vstack([trimesh.sample.sample_surface(cup, 300000, seed=1)[0], trimesh.sample.sample_surface(cap, 300000, seed=1)[0]]))
dd, _ = tree.query(pts)
for lo, hi in ((FLOOR, FLOOR + 3), (FLOOR + 3, FLOOR + 20), (FLOOR + 20, FLOOR + 50), (FLOOR + 50, FLOOR + 68)):
    m = (pts[:, 2] >= lo) & (pts[:, 2] < hi)
    print(f"   z {lo:.1f}..{hi:.1f}: min. luz {dd[m].min():.2f} mm")
print(f"min. luz jajka (z > dno+3): {dd[pts[:, 2] > FLOOR + 3].min():.2f} mm")
# grubosc scian (promien do przeciwnej powierzchni, wzdluz normalnej do wewnatrz)
for nm, m in (("miseczka", cup), ("czapka", cap)):
    p, fi = trimesh.sample.sample_surface(m, 60000, seed=5)
    th_ = thickness(m, p, exterior=False, normals=m.face_normals[fi], method="ray")
    th_ = th_[np.isfinite(th_)]
    # pomin punkty przy krawedziach (nieregularne): wez 0,5 percentyl i minimum absolutne
    print(f"{nm}: grubosc sciany min {th_.min():.2f} | 0,5-percentyl {np.percentile(th_, 0.5):.2f} | mediana {np.median(th_):.2f} mm")
# sciana miedzy gniazdem a wneka czapki
sock = [to_global(socket_solid(), FRe[s]) for s in (+1, -1)]
cav = E["cav_body"]
pc = trimesh.sample.sample_surface(cav, 300000, seed=2)[0]; tc = cKDTree(pc)
for k, sk in enumerate(sock):
    ps = trimesh.sample.sample_surface(sk, 20000, seed=3)[0]
    d, _ = tc.query(ps)
    print(f"gniazdo {k}: najmniejsza sciana do wneki czapki {d.min():.2f} mm")
# pasowanie czop/gniazdo na czapce: czop ucha w gniezdzie czapki
for nm in ["ucho_prawe", "ucho_dlugie_lewe", "poroze_prawe", "poroze_lewe"]:
    m = trimesh.load(OUT + f"/lp_{nm}.stl"); s = +1 if "prawe" in nm else -1
    g = to_global(m, FRe[s])
    ov = abs(inter(g, cap).volume)
    pts_, _ = trimesh.sample.sample_surface(cap, 500000, seed=7)
    dcap, _ = cKDTree(pts_).query(g.vertices)
    a, b, c = FRe[s].to_local(*g.vertices.T)
    print(f"{nm:18s} na czapce: czop min odl. {dcap[b < -0.5].min():.2f} | podstawa {dcap[b > 0.4].min():.2f} | wspolna objetosc {ov:.3f} mm3 | wierzch z={g.bounds[1][2]:.1f}")
