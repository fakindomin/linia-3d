"""KONTROLA STANDARDU v1.0 - jedno polecenie sprawdza 5 modeli kluczowych w obu stylach (zebra rb + lowpoly lp) na GOTOWYCH plikach out/*.stl.
 python3 verify_all.py          -> tabela PASS/FAIL, raport out/_verify_report.json, kod wyjscia 1 przy bledzie
Sprawdza: (1) stale i luz czop-gniazdo 4 pary, (2) nazwy, (3) siatki (szczelnosc, 1 skladowa, nawis), (4) korpus miesci sie w kopercie,
(5) odleglosc P0-powierzchnia (porty z idealnego profilu), (6) MACIERZ PASOWANIA czesc x korpus (zebra i lowpoly, kazdy z kazdym) - interferencja
i luz, (7) wysokosc figurek 150 mm, zgodnosc wymiarow zebra/lowpoly, (8) zebra: rozstaw/amplituda (FFT), (9) lowpoly: reguly M i pierscieni."""
import sys, os, re, json, glob
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import *

OK = []
BAD = []
REP = {}


def check(name, cond, info=""):
    (OK if cond else BAD).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({info})" if str(info) not in ("", "[]") else ""))
    REP[name] = dict(ok=bool(cond), info=str(info))
    return cond


def L(fn, dz=0.0):
    m = trimesh.load(os.path.join(OUT, fn), process=True)
    if dz:
        m.apply_translation([0, 0, dz])
    return m


# ------------------------------------------------------------------ 1. stale i luz czop-gniazdo
print("== 1. interfejs czop / gniazdo ==")
check("czop 5x5x8, gniazdo 5,4x5,4x9 (lib)", (PEG_W, PEG_L, SOCK_W, SOCK_D) == (5.0, 8.0, 5.4, 9.0))
check("pochylenie 14 st., ucha x=+-6, y=0,25", abs(math.degrees(TILT) - 14) < 1e-9 and EAR_X == 6.0 and EAR_Y == 0.25)
mat = peg_socket_matrix()
for k, v in mat.items():
    check(f"luz czop->gniazdo {k} >= {MIN_CLEAR}", v >= MIN_CLEAR, f"{v} mm")
for m in MODELS.values():
    for pn, p in m.ports.items():
        check(f"port {m.name}/{pn}: os jednostkowa, ramka ortonormalna",
              abs(np.linalg.norm(p.frame.B) - 1) < 1e-9 and abs(np.dot(p.frame.A, p.frame.B)) < 1e-9 and abs(np.dot(p.frame.B, p.frame.C)) < 1e-9)
# P0 w modelach = P0 zrodel zebrowanych
check("P0 krolika = shapes.bunny_P0", np.allclose(BUNNY.ports["ear_R"].P0, SH.bunny_P0(1), atol=1e-4), BUNNY.ports["ear_R"].P0.round(3))
check("P0 jajka = shapes.egg_P0", np.allclose(EGG.ports["ear_R"].P0, SH.egg_P0(1), atol=1e-3), EGG.ports["ear_R"].P0.round(3))
check("P0 ogonka dyni = H_TOP - DIP", abs(PUMPKIN.ports["stem"].P0[2] - (BP.H_TOP - BP.DIP)) < 1e-9)
check("P0 nosa / miotly balwana = build_snowman", np.allclose(SNOWMAN.ports["nose"].P0, BS.P_NOSE) and np.allclose(SNOWMAN.ports["broom"].P0, BS.P_BROOM))

# ------------------------------------------------------------------ 2. nazwy
print("== 2. nazwy plikow ==")
RB_FILES = ["korpus_bazowy", "krolik_calosc", "renifer_calosc", "ucho_prawe", "ucho_lewe", "ucho_dlugie_prawe", "ucho_dlugie_lewe", "poroze_prawe",
            "poroze_lewe", "jajko_miseczka", "jajko_czapka_gniazda", "jajko_czapka_uszy", "jajko_czapka_uszy_dlugie", "dynia_korpus",
            "dynia_korpus_platy", "dynia_ogonek", "balwan", "balwan_nos", "balwan_miotla"]
LP_FILES = ["lp_" + n for n in RB_FILES if n not in ()]
bad_names = [f for f in RB_FILES + LP_FILES if not re.match(NAME_RE, f + ".stl")]
check("nazwy zgodne z NAME_RE, lowpoly z prefiksem lp_", not bad_names, bad_names)
missing = [f for f in RB_FILES + LP_FILES if not os.path.exists(os.path.join(OUT, f + ".stl"))]
check("komplet plikow (19 zebra + 19 lowpoly)", not missing, missing)

# ------------------------------------------------------------------ 3. siatki
print("== 3. siatki ==")
UPRIGHT = lambda n: not any(t in n for t in ("ucho", "poroze", "nos", "miotla"))
PORTS_OF = lambda n: (list(BUNNY.ports.values()) if "korpus_bazowy" in n else list(EGG.ports.values()) if "czapka_gniazda" in n else
                      list(PUMPKIN.ports.values()) if n.endswith("dynia_korpus") or n.endswith("dynia_korpus_platy") else
                      list(SNOWMAN.ports.values()) if n.endswith("balwan") else [])
M = {}
for n in RB_FILES + LP_FILES:
    if n in missing:
        continue
    M[n] = L(n + ".stl")
    r = mesh_report(M[n], UPRIGHT(n) and "dynia_ogonek" not in n, PORTS_OF(n), noise_frac=0.0 if n.startswith("lp_") else 0.01)
    ok = r["watertight"] and r["winding"] and r["components"] == 1 and r["volume"] > 0 and abs(r["zmin"]) < 0.05
    if "overhang" in r:
        ok = ok and (r["overhang"]["ok"] or n in RB_FILES[:0])
    check(f"siatka {n}", ok, f"{r['ext']} tri {r['tris']}" + (f" nawis {r['overhang']['steep_mm2']} mm2, mostki {[b[1] for b in r['overhang']['bridges']]}" if "overhang" in r else ""))

# ------------------------------------------------------------------ 4. koperta
print("== 4. korpus miesci sie w kopercie modelu (zebra i lowpoly) ==")
BODIES = {"korpus_bazowy": (BUNNY, 0.0), "jajko_miseczka": (EGG, 0.0), "jajko_czapka_gniazda": (EGG, SH.ZM + 0.2), "dynia_korpus": (PUMPKIN, 0.0),
          "dynia_korpus_platy": (PUMPKIN, 0.0), "balwan": (SNOWMAN, 0.0)}
for base, (model, dz) in BODIES.items():
    for pre in ("", "lp_"):
        n = pre + base
        if n in M:
            V = M[n].vertices
            ex = float(-model.env.sdf(V[:, 0], V[:, 1], V[:, 2] + dz).min())
            check(f"koperta {n}", ex <= ENV_TOL, f"wystawanie {ex:+.3f} mm (tol {ENV_TOL})")

# ------------------------------------------------------------------ 5. odleglosc P0 - powierzchnia
print("== 5. porty: odleglosc P0 od powierzchni (bryla bez gniazda) ==")
SOL = pickle.load(open(OUT + "/_lp_std.pkl", "rb"))["bodies"]
LPS = {"krolik": (SOL["bunny"], BUNNY), "jajko": (SOL["egg_full"], EGG), "dynia": (SOL["pump_sm"], PUMPKIN), "balwan": (SOL["snow"], SNOWMAN)}
for nm, (solid, model) in LPS.items():
    for pn, p in model.ports.items():
        d = port_deviation(solid, p)
        check(f"lowpoly {nm}/{pn}: |P0 - powierzchnia| <= {PORT_TOL}", d <= PORT_TOL, f"{d:.2f} mm")


def rb_port_dist(model, pn):
    p = model.ports[pn]
    ax, ay, az = [np.arange(-1.6, 1.61, 0.05) + c for c in p.P0]
    X, Y, Z = np.meshgrid(ax, ay, az, indexing="ij")
    F = model.ribbed_F(X, Y, Z)
    m = np.abs(F) < 0.04
    d = np.sqrt((X - p.P0[0]) ** 2 + (Y - p.P0[1]) ** 2 + (Z - p.P0[2]) ** 2)
    return float(d[m].min()) if m.any() else 9.9


for model in (BUNNY, EGG, PUMPKIN, SNOWMAN):
    for pn in model.ports:
        d = rb_port_dist(model, pn)
        check(f"zebra {model.name}/{pn}: |P0 - powierzchnia| <= {PORT_TOL}", d <= PORT_TOL, f"{d:.2f} mm")

# ------------------------------------------------------------------ 6. macierz pasowania
print("== 6. MACIERZ PASOWANIA: kazda czesc x kazdy korpus (zebra i lowpoly) ==")
Rm_inv = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)     # (a, c, -b) -> (a, b, c) przed przesunieciem


def part_global(n, model, pn):
    m = M[n].copy()
    if "ogonek" in n:                                  # druk do gory nogami: z' = s - b, y' = c (s = STEM_H)
        V = m.vertices.copy()
        loc = np.c_[V[:, 0], BP.STEM_H - V[:, 2], V[:, 1]]
        m = trimesh.Trimesh(loc, m.faces.copy(), process=False)
        trimesh.repair.fix_normals(m)
        if m.volume < 0:
            m.invert()
    return to_global(m, model.ports[pn].frame)


EAR_PARTS = [f"{p}_{s}" for p in ("ucho", "ucho_dlugie", "poroze", "ucho_mis", "ucho_kot", "ucho_lis", "ucho_sowa") for s in ("prawe", "lewe")]
CASES = []     # (nazwa czesci, model, port, [(korpus, dz)])
for pn_part in EAR_PARTS:
    side = "ear_R" if pn_part.endswith("prawe") else "ear_L"
    for pre in ("", "lp_"):
        n = pre + pn_part
        if n not in M and not os.path.exists(os.path.join(OUT, n + ".stl")):
            continue
        if n not in M:
            M[n] = L(n + ".stl")
        CASES.append((n, BUNNY, side, ["korpus_bazowy", "lp_korpus_bazowy"], 0.0))
        CASES.append((n, EGG, side, ["jajko_czapka_gniazda", "lp_jajko_czapka_gniazda"], SH.ZM + 0.2))
for pre in ("", "lp_"):
    CASES.append((pre + "dynia_ogonek", PUMPKIN, "stem", ["dynia_korpus", "dynia_korpus_platy", "lp_dynia_korpus", "lp_dynia_korpus_platy"], 0.0))
    CASES.append((pre + "balwan_nos", SNOWMAN, "nose", ["balwan", "lp_balwan"], 0.0))
    CASES.append((pre + "balwan_miotla", SNOWMAN, "broom", ["balwan", "lp_balwan"], 0.0))
cross = 0
for n, model, pn, bodies, dz in CASES:
    if n not in M:
        continue
    g = part_global(n, model, pn)
    for b in bodies:
        if b not in M:
            continue
        body = M[b].copy()
        body.apply_translation([0, 0, dz])
        iv = interference(g, body)
        a_, b_, c_ = model.ports[pn].frame.to_local(*g.vertices.T)
        tree = surf_tree(body, 400000)
        dd, _ = tree.query(g.vertices)
        in_peg = (np.abs(a_) <= 2.51) & (c_ >= -0.01) & (c_ <= 5.01) & (b_ <= 2.01)      # czop (b<=2) nie liczy sie jako podstawa
        d_base = float(dd[(b_ > 0.4) & ~in_peg].min())
        d_peg = float(dd[b_ < -0.5].min())
        style_p = "lp" if n.startswith("lp_") else "rb"
        style_b = "lp" if b.startswith("lp_") else "rb"
        tag = "" if style_p == style_b else "  [KRZYZOWE]"
        cross += style_p != style_b
        ok = iv <= 1.0 and d_base >= MIN_CLEAR and d_peg >= MIN_CLEAR
        check(f"pasowanie {n} -> {b} ({model.name}/{pn})", ok, f"interferencja {iv:.2f} mm3, podstawa {d_base:.2f}, czop {d_peg:.2f} mm{tag}")
print(f"   (w tym par krzyzowych zebra<->lowpoly: {cross})")

# ------------------------------------------------------------------ 7. wysokosci i wymiary
print("== 7. wysokosci figurek i zgodnosc wymiarow zebra / lowpoly ==")
for n in ("krolik_calosc", "renifer_calosc"):
    for pre in ("", "lp_"):
        z = M[pre + n].extents[2]
        check(f"wysokosc {pre + n} = {TOTAL_H:.0f} mm", abs(z - TOTAL_H) <= 0.35, f"{z:.2f}")
check("wysokosc balwan = 150", all(abs(M[p + "balwan"].extents[2] - TOTAL_H) <= 0.1 for p in ("", "lp_")))
for base in ("korpus_bazowy", "jajko_miseczka", "jajko_czapka_gniazda", "dynia_korpus", "dynia_korpus_platy", "balwan", "krolik_calosc", "renifer_calosc"):
    e1, e2 = M[base].extents, M["lp_" + base].extents
    # ramiona renifera / uszy - dopuszczamy rozjazd w poziomie; wysokosc musi byc zgodna
    dz_ = abs(e1[2] - e2[2])
    dxy = max(abs(e1[0] - e2[0]), abs(e1[1] - e2[1]))
    check(f"wymiary zebra vs lowpoly {base}", dz_ <= 1.0 and dxy <= 3.0, f"dz {dz_:.2f}, dxy {dxy:.2f} mm")

# ------------------------------------------------------------------ 8. zebra: rozstaw i amplituda
print("== 8. zebra: rozstaw ~3,4 mm i amplituda (FFT przekroju) ==")


def rib_check(fn, z, expect, dz=0.0):
    return rib_spectrum(M[fn], z)


for fn, z, expect in (("korpus_bazowy", 45, 36), ("balwan", 24, 52), ("balwan", 63, 42), ("balwan", 87.5, 32), ("balwan", 130, 24),
                      ("jajko_miseczka", 20, 48), ("dynia_korpus", 32, 92), ("dynia_korpus_platy", 32, 36)):
    k, pitch, pp = rib_check(fn, z, expect)
    check(f"zebra {fn} z={z}: N={k} (oczek. {expect}), rozstaw {pitch:.2f}, amplituda p-p {pp:.2f}",
          k == expect and (3.0 <= pitch <= 3.8 or fn == "dynia_korpus_platy") and 1.2 <= pp <= 2.1 or fn == "dynia_korpus_platy" and k == expect)

# ------------------------------------------------------------------ 9. lowpoly: reguly
print("== 9. lowpoly: M = facet_M(Rmax sekcji), pierscienie w tolerancji ==")
secs = snowman_sections()
Rsec = [(Rs, 0.0, 47.15), (Rs, 47.95, SNOWMAN.ports["broom"].P0[2]), (Rs, SNOWMAN.ports["broom"].P0[2] + 1.5, BS.ZT), (Rs, BS.ZT + 1e-3, BS.TOTAL)]
for i, (s, (R_, z0, z1)) in enumerate(zip(secs, Rsec)):
    want = section_M(Rs if i else clamp_overhang(Rs, 0.0)[0], z0, z1)
    got = s[0]["M"]
    check(f"balwan sekcja {i + 1}: M = {got} (facet_M = {want})", got == want, f"zakres z {z0:.1f}..{z1:.1f}")
rg = lp_section_rings(BUNNY.Rfun, 0.0, 121.0, port_zs=[BUNNY.zport], apex_top=True)
check(f"krolik: M = {rg[0]['M']} (facet_M = {section_M(BUNNY.Rfun, 0, 121)})", rg[0]["M"] == section_M(BUNNY.Rfun, 0, 121))


def ring_dev(rings, R):
    """odleglosc Hausdorffa lamanej pierscieni (z, r rownowazne) od profilu idealnego R(z) [mm] (w plaszczyznie rho-z; kopuly licza sie prawidlowo)"""
    z = np.array([r["z"] for r in rings])
    rr = np.array([max(R(zi), 0.0) for zi in z])
    zz = np.linspace(z[0], z[-1], 3000)
    ideal = np.array([max(R(x), 0.0) for x in zz])
    return float(shapely.hausdorff_distance(sg.LineString(np.c_[rr, z]), sg.LineString(np.c_[ideal, zz]), 0.01))


check("krolik: odchylka pierscieni od profilu <= LP_TOL + 0,2", ring_dev(rg, BUNNY.Rfun) <= LP_TOL + 0.2, f"{ring_dev(rg, BUNNY.Rfun):.2f} mm")
ve = SOL["bunny"].volume / (2 * math.pi * BUNNY.env.poly.area * 0 + 1)
Vid = lambda model: 2 * math.pi * sg.Polygon(model.outline).centroid.x * sg.Polygon(model.outline).area
for nm, solid, model in (("krolik", SOL["bunny"], BUNNY), ("balwan", SOL["snow"], SNOWMAN), ("jajko", SOL["egg_full"], EGG)):
    r = solid.volume / Vid(model)
    check(f"objetosc lowpoly/idealna {nm}: {r:.3f} (0,95..1,03)", 0.95 <= r <= 1.03)

# ------------------------------------------------------------------ podsumowanie
print(f"\nWYNIK: {len(OK)} PASS, {len(BAD)} FAIL")
if BAD:
    print("FAIL:", *BAD, sep="\n  ")
json.dump(REP, open(OUT + "/_verify_report.json", "w"), indent=1, ensure_ascii=False)
sys.exit(1 if BAD else 0)
