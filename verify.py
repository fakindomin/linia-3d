import sys, glob, os, json, math
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from lib import OUT
files = sorted(f for f in glob.glob(OUT + "/*.stl") if not os.path.basename(f).startswith("_"))
rows = []
print(f"{'plik':38s} {'wymiary [mm]':22s} {'trojk.':>8s} {'MB':>5s}  wt  spojn. skladowe  obj.[cm3]")
for f in files:
    m = trimesh.load(f, process=True)
    comps = len(m.split(only_watertight=False))
    e = m.extents
    rows.append((os.path.basename(f), e, len(m.faces), os.path.getsize(f) / 1e6, m.is_watertight, m.is_winding_consistent, comps, m.volume / 1000))
    print(f"{os.path.basename(f):38s} {e[0]:6.1f} x {e[1]:5.1f} x {e[2]:5.1f}  {len(m.faces):8,d} {os.path.getsize(f)/1e6:5.1f}  {str(m.is_watertight):5s} {str(m.is_winding_consistent):5s} {comps:3d}  {m.volume/1000:8.1f}")

def rib_check(path, z, expect, label):
    m = trimesh.load(path, process=True)
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    lines = sorted(sec.discrete, key=lambda l: -np.mean(np.hypot(np.array(l)[:, 0], np.array(l)[:, 1])))
    pts = np.array(lines[0])[:, :2]
    ctr = np.array([0.0, 0.0])
    th = np.arctan2(pts[:, 1], pts[:, 0]); r = np.hypot(pts[:, 0], pts[:, 1])
    o = np.argsort(th); th, r = th[o], r[o]
    grid = np.linspace(-np.pi, np.pi, 4096, endpoint=False)
    rg = np.interp(grid, th, r, period=2 * np.pi)
    sp = np.abs(np.fft.rfft(rg - rg.mean()))
    k = int(np.argmax(sp[5:200]) + 5)
    # amplituda zeber: odchylenie od gladkiej obwiedni (usun harmoniczne < k/2)
    F = np.fft.rfft(rg); F[: k // 2] = 0
    rr = np.fft.irfft(F, 4096)
    pp = np.percentile(rr, 99) - np.percentile(rr, 1)
    rm = rg.mean()
    print(f"{label:30s} z={z:6.1f}: zeber {k:3d} (oczekiwane {expect}) | rozstaw {2*np.pi*rm/k:4.2f} mm | amplituda p-p {pp:4.2f} mm | R sr. {rm:5.1f}")

print("\nKontrola zeber (FFT przekroju):")
rib_check(OUT + "/korpus_bazowy.stl", 45, 36, "krolik/renifer korpus")
rib_check(OUT + "/korpus_bazowy.stl", 105, 36, "krolik/renifer glowa")
rib_check(OUT + "/balwan.stl", 24, 52, "balwan kula 1")
rib_check(OUT + "/balwan.stl", 63, 42, "balwan kula 2")
rib_check(OUT + "/balwan.stl", 87.5, 32, "balwan glowa")
rib_check(OUT + "/balwan.stl", 130, 24, "balwan kapelusz")
rib_check(OUT + "/jajko_miseczka.stl", 20, 48, "jajko miseczka")
rib_check(OUT + "/dynia_korpus.stl", 32, 92, "dynia drobne zebra")
rib_check(OUT + "/dynia_korpus_platy.stl", 32, 36, "dynia 36 platow")
