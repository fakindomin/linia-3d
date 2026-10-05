import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from scipy.spatial import cKDTree
D = pickle.load(open(OUT + "/_lp_dynia.pkl", "rb")); FR = D["FR_STEM"]
st = D["stem_local"]
for nm in ("lp_dynia_korpus", "lp_dynia_korpus_platy", "lp_dynia_ogonek"):
    m = trimesh.load(OUT + f"/{nm}.stl")
    n = m.face_normals; low = n[:, 2] < -1e-3; ang = np.degrees(np.arccos(np.clip(-n[:, 2], 0, 1)))
    horiz = low & (ang < 1.0); inc = low & ~horiz
    mx = (90 - ang[inc]).max() if inc.any() else 0
    print(f"{nm:24s} wt {m.is_watertight} comp {len(m.split(only_watertight=False))} | poziome w dol: {m.area_faces[horiz].sum():.0f} mm2 (z={np.unique(np.round(m.triangles_center[horiz,2],1)).tolist()}) | max nawis nie-poziomy {mx:.1f} st. od pionu")
for nm, key in (("smooth", "body_sm"), ("platy", "body_lb")):
    body = D[key]
    pts, _ = trimesh.sample.sample_surface(body, 600000, seed=1); T = cKDTree(pts)
    g = to_global(st, FR); a, b, c = FR.to_local(*g.vertices.T)
    d, _ = T.query(g.vertices)
    ov = abs(inter(g, body).volume)
    print(f"ogonek na dyni {nm}: czop-gniazdo min {d[b < -0.5].min():.2f} | podstawa min {d[b > 0.4].min():.2f} | wspolna objetosc {ov:.3f} mm3 | wierzch z={g.bounds[1][2]:.1f}")
print("ogonek: ext lokalny", st.extents.round(1).tolist())
