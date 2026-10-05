"""Pasowanie lowpoly: min. odleglosc podstawy ucha/poroza od korpusu i jajka + czop w gniezdzie, kolizje (objetosc przeciecia)"""
import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
P = pickle.load(open(OUT + "/_lp_frames.pkl", "rb"))
FRb, FRe = P["FRb"], P["FRe"]
body = body_solid(); egg = egg_outer_full()
body_s = trimesh.load(OUT + "/lp_korpus_bazowy.stl"); body_s.apply_translation([0, 0, 0])   # korpus stoi na stole z=0 (bez przesuniecia)
print("korpus: z min", body_s.bounds[0][2])
from scipy.spatial import cKDTree
def tree(m, n=300000):
    pts, _ = trimesh.sample.sample_surface(m, n, seed=1); return cKDTree(pts)
tb = tree(body); te = tree(egg)
sock = {}
for nm in ["ucho_prawe", "ucho_lewe", "ucho_dlugie_prawe", "ucho_dlugie_lewe", "poroze_prawe", "poroze_lewe"]:
    m = trimesh.load(OUT + f"/lp_{nm}.stl")
    # save_lp przesunal czesc do stolu: odtworz polozenie lokalne (c min = 0 -> bez zmian, bo c min = 0)
    s = +1 if "prawe" in nm else -1
    for lab, FR, T, solid in (("korpus", FRb, tb, body), ("jajko", FRe, te, egg)):
        g = to_global(m, FR[s])
        a, b, c = FR[s].to_local(*g.vertices.T)
        d, _ = T.query(g.vertices)
        # kolizja: objetosc czesci wewnatrz bryly
        inter_v = abs(inter(g, solid).volume) if True else 0
        print(f"{nm:20s} na {lab:7s}: min odl. podstawa(b>0.4) {d[b > 0.4].min():.2f} | czop(b<-0.5) {d[b < -0.5].min():.2f} | "
              f"objetosc w bryle {inter_v:.2f} mm3 | wierzch z={g.bounds[1][2]:.2f}")
