"""SZABLON NOWEGO MODELU wg STANDARD v1.0  -  demo: GRUSZKA z dwoma listkami (zebra + lowpoly), caly kod z JEDNEGO modulu: standard.py.

Zasada: kopiujesz ten plik, zmieniasz sekcje "1. DANE MODELU" (profil R(z), porty) i uzupelniasz nazwy/czesci. Nic nie wolno
odczytywac z innych modeli (krolik, jajko, ...) - wszystko jest w standard.py (stale, reguly, narzedzia, kontrola).

 python3 new_model_template.py          -> out_demo/gruszka_*.stl (zebra) + out_demo/lp_gruszka_*.stl (lowpoly) + kontrola verify_set
"""
import sys, time
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standard import *                      # stale, Model, Port, ear_ports, Envelope, ribbed_sections_F, lp_section_rings, lp_revolve, lp_trim, emit, verify_set ...
from lp_parts import ear_leaf               # czesc wymienna lowpoly (lisc)
from parts import ear_flat                  # czesc wymienna zebrowana (lisc)

T0 = time.time()
OUT = set_out(os.path.join(HERE, "out_demo"))   # demo nie zasmieca out/ - w prawdziwym modelu pomijasz te linie (OUT = katalog wynikow)

# =====================================================================================================
# 1. DANE MODELU: jeden idealny (gladki) profil R(z) - ten sam dla zeber i lowpoly; z = 0 to stol
# =====================================================================================================
R1, Z1 = 26.0, 20.0           # dolna kula: Z1 / R1 = 0,77 < 0,82 -> podstawa plaska i nawis <= 55 st. bez podpor
R2, Z2 = 17.0, 56.0           # gorna kula (glowka gruszki)
H = Z2 + R2                   # 73 mm
P_SM = 14.0                   # gladkie laczenie kul (jak bałwan)


def R(z):
    z = np.asarray(z, np.float64)
    b = lambda zc, Rc: Rc * np.sqrt(np.clip(1 - ((z - zc) / Rc) ** 2, 0, None))
    return (b(Z1, R1) ** P_SM + b(Z2, R2) ** P_SM) ** (1 / P_SM)


zz_ = np.linspace(35, 50, 3001)
Z_NECK = float(zz_[np.argmin(R(zz_))])                         # 'talia' = granica sekcji (zebra: inne N, lowpoly: inne M)
LEAF_L = 22.0                                                  # widoczna dlugosc listka [mm]

# porty z IDEALNEGO profilu (standard: ucha x = +-6, y = 0,25, pochylenie 14 st.); P0 lezy na powierzchni R(z)
ports = ear_ports(lambda z: float(R(z)), 62.0, H)
PEAR = Model("gruszka", outline_R(lambda z: float(R(z)), 0.0, H), ports=ports,
             ribbed_F=ribbed_sections_F(R, 0.0, H, cuts=(Z_NECK,)))      # N zeber w kazdej sekcji ~ 2 pi Rmax / 3,4
print(f"gruszka: H {H:.1f}, talia z={Z_NECK:.2f}, N zeber {[s[2] for s in PEAR.ribbed_F.sections]}, "
      f"P0 ucha {PEAR.ports['ear_R'].P0.round(2)}")

SIDES = ((+1, "prawe", "ear_R"), (-1, "lewe", "ear_L"))
BODIES, PARTS, SOLIDS = {}, {}, {}

# =====================================================================================================
# 2. STYL ZEBROWANY (rb): pole F -> marching cubes -> gniazda -> zapis; czesci: przyciete do KOPERTY modelu
# =====================================================================================================
VOX = 0.35
axes, (X, Y, Z) = make_grid(-30, 30, -30, 30, -1.0, H + 1.5, VOX)
F = PEAR.ribbed_F(X, Y, Z)
for p in PEAR.ports.values():
    a, b, c = p.frame.to_local(X, Y, Z)
    F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
body_rb = decimate(mesh_from_F(F, axes, VOX), 200000, label="gruszka")
emit(body_rb, "gruszka_korpus.stl", True, "2 gniazda na listki", style="rb", ports=list(PEAR.ports.values()))
BODIES["gruszka_korpus.stl"] = dict(mesh=trimesh.load(os.path.join(OUT, "gruszka_korpus.stl")), ports=["ear_R", "ear_L"])
for s, nm, pn in SIDES:
    leaf = part_mesh(ear_flat(LEAF_L), rb_trims([(PEAR, pn)]), True, (-10, 10), (-9, LEAF_L + 3), 0.2)
    emit(leaf, f"gruszka_listek_{nm}.stl", False, "druk na plecach; czop 5x5x8", style="rb")
    PARTS[f"gruszka_listek_{nm}.stl"] = dict(mesh=trimesh.load(os.path.join(OUT, f"gruszka_listek_{nm}.stl")), port=pn)

# =====================================================================================================
# 3. STYL LOWPOLY (lp): sekcje z pierscieni (M wg promienia sekcji) -> gniazda -> zapis; czesci przyciete do TEJ SAMEJ koperty
# =====================================================================================================
Rf = lambda z: float(R(z))
zport = PEAR.ports["ear_R"].P0[2]
secs = [lp_section_rings(Rf, 0.0, Z_NECK - 0.4),                                       # kula dolna: M = facet_M(26) = 14
        lp_section_rings(Rf, Z_NECK + 0.4, H, port_zs=[zport], apex_top=True)]         # glowka: M = 8, pierscien portu z faseta na osi x
solid = lp_revolve(secs)
for pn, p in PEAR.ports.items():
    print(f"lowpoly {pn}: |P0 - powierzchnia| = {port_deviation(solid, p):.2f} mm (<= {PORT_TOL})")
SOLIDS["lp"] = solid
body_lp = cut_ports(solid, PEAR)
emit(body_lp, "lp_gruszka_korpus.stl", True, "2 gniazda na listki", style="lp", ports=list(PEAR.ports.values()))
BODIES["lp_gruszka_korpus.stl"] = dict(mesh=trimesh.load(os.path.join(OUT, "lp_gruszka_korpus.stl")), ports=["ear_R", "ear_L"])
for s, nm, pn in SIDES:
    leaf = lp_trim(ear_leaf(LEAF_L, -3.0), [(PEAR, pn)])
    emit(leaf, f"lp_gruszka_listek_{nm}.stl", False, "druk na plecach; czop 5x5x8", style="lp")
    PARTS[f"lp_gruszka_listek_{nm}.stl"] = dict(mesh=trimesh.load(os.path.join(OUT, f"lp_gruszka_listek_{nm}.stl")), port=pn)

# =====================================================================================================
# 4. KONTROLA (te same kryteria co verify_all.py): nazwy, siatki, nawisy, koperta, P0, pasowanie 2 x 4 (takze krzyzowe), zebra
# =====================================================================================================
print("== kontrola standardu ==")
rib_z = [("gruszka_korpus.stl", 20.0, PEAR.ribbed_F.sections[0][2]), ("gruszka_korpus.stl", 62.0, PEAR.ribbed_F.sections[1][2])]
n_ok, bad = verify_set(PEAR, BODIES, PARTS, solids=SOLIDS, rib_z=rib_z)
print(f"czas {time.time() - T0:.0f} s")
sys.exit(1 if bad else 0)
