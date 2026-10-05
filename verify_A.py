import sys, glob, os
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from lib import OUT, n_ribs
names = ["ucho_mis_prawe","ucho_mis_lewe","ucho_kot_prawe","ucho_kot_lewe","ucho_lis_prawe","ucho_lis_lewe","ucho_sowa_prawe","ucho_sowa_lewe",
         "mis_calosc","kot_calosc","lis_calosc","sowa_calosc","aniol_calosc","jajko_czapka_pisklo",
         "czapka_krasnal","czapka_mikolaj","jajko_czapka_krasnal","jajko_czapka_mikolaj","duszek"]
print(f"{'plik':28s} {'wymiary [mm]':24s} {'trojk.':>8s} {'MB':>5s} wt  spojn skl obj[cm3]")
bad = 0
for n in names:
    f = f"{OUT}/{n}.stl"
    m = trimesh.load(f, process=True)
    comps = len(m.split(only_watertight=False))
    e = m.extents
    ok = m.is_watertight and m.is_winding_consistent and comps == 1 and m.volume > 0 and os.path.getsize(f) < 25e6
    bad += (not ok)
    print(f"{n+'.stl':28s} {e[0]:6.1f} x {e[1]:5.1f} x {e[2]:5.1f}  {len(m.faces):8,d} {os.path.getsize(f)/1e6:5.1f}  {str(m.is_watertight):5s} {str(m.is_winding_consistent):5s} {comps:2d} {m.volume/1000:8.1f}  {'OK' if ok else 'PROBLEM'}")
print("problemy:", bad)

def rib_check(path, z, expect, label):
    m = trimesh.load(path, process=True)
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    lines = sorted(sec.discrete, key=lambda l: -np.mean(np.hypot(np.array(l)[:, 0], np.array(l)[:, 1])))
    pts = np.array(lines[0])[:, :2]
    th = np.arctan2(pts[:, 1], pts[:, 0]); r = np.hypot(pts[:, 0], pts[:, 1])
    o = np.argsort(th); th, r = th[o], r[o]
    grid = np.linspace(-np.pi, np.pi, 4096, endpoint=False)
    rg = np.interp(grid, th, r, period=2 * np.pi)
    sp = np.abs(np.fft.rfft(rg - rg.mean()))
    k = int(np.argmax(sp[5:200]) + 5)
    F = np.fft.rfft(rg); F[: k // 2] = 0
    rr = np.fft.irfft(F, 4096)
    pp = np.percentile(rr, 99) - np.percentile(rr, 1)
    rm = rg.mean()
    print(f"{label:28s} z={z:6.1f}: zeber {k:3d} (oczek. {expect}) | rozstaw {2*np.pi*rm/k:4.2f} mm | ampl. p-p {pp:4.2f} mm | R sr. {rm:5.1f}")
print("\nzebra:")
rib_check(OUT + "/mis_calosc.stl", 45, 36, "mis korpus")
rib_check(OUT + "/czapka_krasnal.stl", 6, n_ribs(19.7), "czapka krasnal (dol)")
rib_check(OUT + "/czapka_mikolaj.stl", 20, n_ribs(20.5), "czapka Mikolaj (stozek)")
rib_check(OUT + "/jajko_czapka_krasnal.stl", 70.0 - 34.2, n_ribs(23.2), "jajko-krasnal (stozek)")
rib_check(OUT + "/duszek.stl", 40, 46, "duszek")
rib_check(OUT + "/jajko_czapka_pisklo.stl", 60 - 34.2, 48, "jajko-pisklo")

# czapki jajka: dolna czesc (otwor/kolnierz) identyczna jak w czapce z gniazdami (przekroje dla z < 30 mm od dolu)
ref = trimesh.load(OUT + "/jajko_czapka_gniazda.stl")
for n in ("jajko_czapka_pisklo", "jajko_czapka_krasnal", "jajko_czapka_mikolaj"):
    m = trimesh.load(f"{OUT}/{n}.stl")
    diffs = []
    for z in (1.0, 4.0, 8.0, 14.0, 20.0, 28.0):
        a = [abs(trimesh.load_path(s.vertices[:, :2]).area) if False else 0 for s in []]
        sa = ref.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]); sb = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        pa = sa.to_2D()[0].polygons_full; pb = sb.to_2D()[0].polygons_full
        diffs.append(abs(sum(p.area for p in pa) - sum(p.area for p in pb)))
    print(f"{n}: roznica pola przekroju u dolu vs czapka z gniazdami: max {max(diffs):.2f} mm2")
