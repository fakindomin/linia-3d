"""RENIFER KREGIEL: smukly korpus w ksztalcie kregla (szyja, jajowata glowa), poroze o 3 poziomach i boczne uszy-liscie.
Parametry (ten sam zestaw co suwaki w podgladzie 'Zebrowana kolekcja'; podglad czyta je z line.json) + budowa STL wg STANDARD v1.0:
  renifer_kregiel_calosc.stl                      poroze i uszy przytopione (jeden wydruk)
  renifer_kregiel_korpus.stl + _poroze_{prawe,lewe}.stl   poroze wymienne na czopie 5x5x8 (gniazda w glowie), uszy przytopione
Uzycie:  python renifer_kregiel.py            (wyniki w out/)
"""
import math, os, sys, time
import numpy as np
import shapes as SH
from standard import *                      # Model, Port, outline_R, rb_trims, emit, verify_set, make_grid, mesh_from_F, socket_F, part_fn, part_mesh, mount_frame ...
from parts import ANT_ANGLE, antler_flat, antler_geom, leaf_flat

# --- parametry (domyslne = wzor ze zdjecia); klucze jak w suwakach podgladu
BODY = SH.body_params(sil=1, bodyW=53.0, baseR=16.5, bellyZ=48.0, shZ=73.0, shR=17.0, neckZ=86.0, neckR=13.8, headR=18.5, headZ=104.0, headK=1.0,
                      blend=9.0, ribs=44)          # sylwetka z punktow (sil = 1): podstawa, brzuch, barki, szyja + glowa; dopasowana do zdjecia (rms 0,3 mm)
MOUNT = dict(earX=11.5, earTilt=12.0, earPitch=0.0, earT=5.0)                # poroze: rozstaw gniazd, kat na zewnatrz, kat przod/tyl, grubosc
ANT = dict(antS=1.0, antW=1.0, antLv=2, antSp=13.0, antTine=1.0, antAng=round(ANT_ANGLE, 3))   # = dawne poroze renifera (2 poziomy), domyslne suwaki poroza
ANT_K = dict(ANT, antW=1.35, antLv=3, antAng=44.0, antIn=1)                  # kregiel: 3 poziomy, grubsze galezie, odnogi do srodka (jak na zdjeciu; antIn = 0 daje dawny uklad)
LEAF = dict(leafL=17.0, leafW=10.0, leafT=3.4, leafAng=55.0, leafPos=60.0)   # boczne uszy-liscie: dlugosc, szerokosc, grubosc, kat od pionu, polozenie (kat od czubka glowy)


def params():
    """plaski slownik parametrow (do line.json i do podgladu)"""
    return {**BODY, **MOUNT, **ANT_K, **LEAF}


# =====================================================================================================
# GEOMETRIA: ramki mocowania, model standardu (porty poroza), pola 3D
# =====================================================================================================
def ant_frame(side, par=None):
    """ramka mocowania poroza (port): P0 na szczycie glowy (x = +-earX), kat na zewnatrz earTilt, przod/tyl earPitch"""
    P = par or params()
    return mount_frame(side, SH.bunny_P0(side, P, P["earX"]), math.radians(P["earTilt"]), math.radians(P["earPitch"]))


def leaf_frame(side, par=None):
    """ramka bocznego ucha-liscia: punkt na powierzchni glowy pod katem leafPos od czubka, os ucha o leafAng od pionu"""
    P = par or params()
    return mount_frame(side, SH.head_port(side, P, P["leafPos"], P["leafT"]), math.radians(P["leafAng"]), 0.0)


def ant_ar(side, par=None):
    """zakres lokalnej osi a poroza po stronie side: odnogi na zewnatrz (antIn = 0) albo do srodka (antIn = 1, jak na zdjeciu)"""
    P = par or params()
    G = antler_geom(P["antLv"], P["antSp"], P["antTine"], P["antAng"], P["antS"])
    return (-10, G["AR"]) if (side > 0) != bool(P.get("antIn", 0)) else (-G["AR"], 10)


def ant_part(mirror, par=None, res=0.1):
    """plaskie poroze; mirror = strona lewa (jak dawniej), a antIn = 1 odwraca odnogi do srodka"""
    P = par or params()
    mirror = bool(mirror) != bool(P.get("antIn", 0))
    return antler_flat(res, mirror, levels=P["antLv"], spacing=P["antSp"], tine=P["antTine"], angle=P["antAng"], s=P["antS"], w=P["antW"], T=P["earT"])


def leaf_part(par=None, res=0.1):
    P = par or params()
    return leaf_flat(P["leafL"], P["leafW"], P["leafT"], res)


def make_model(par=None):
    """Model wg STANDARD v1.0: idealny obrys korpusu (profil p-normy), porty poroza ear_R / ear_L z ramka mocowania renifera"""
    P = par or params()
    Rk = lambda z: float(SH.bunny_profile(np.float64(z), P))
    H = P["headZ"] + P["headR"] * P["headK"]
    ports = {("ear_R" if s > 0 else "ear_L"): Port("ear_R" if s > 0 else "ear_L", SH.bunny_P0(s, P, P["earX"]), ant_frame(s, P), "ear") for s in (+1, -1)}
    m = Model("renifer_kregiel", outline_R(Rk, 0.0, H), ports=ports, ribbed_F=lambda X, Y, Z: SH.bunny_F(X, Y, Z, P))
    m.Rfun = Rk
    return m


def _frame_box(fr, ar, br, cr):
    pts = np.array([fr.O + a * fr.A + b * fr.B + c * fr.C for a in ar for b in br for c in cr])
    return pts.min(0), pts.max(0)


def extents(par=None):
    """pudelko siatki obliczen (xh, ylo, yhi, zhi): obejmuje korpus oraz lokalne pudelka poroza i uszu-lisci w ich ramkach (jak w podgladzie, buildReal)"""
    P = par or params()
    G = antler_geom(P["antLv"], P["antSp"], P["antTine"], P["antAng"], P["antS"])
    rmax = max(P["bodyW"] / 2, P["baseR"] if P.get("sil") else 0.0)
    xh, ylo, yhi = max(21.0, rmax + 2.5), -max(21.0, rmax + 2.5), max(21.0, rmax + 2.5)
    zhi = SH.bunny_P0(1, P, P["earX"])[2] + 6
    A = P["leafW"] / 2 + 2
    for fr_fn, sd_ar, L in ((ant_frame, lambda s: ant_ar(s, P), G["Lc"]), (leaf_frame, lambda s: (-A, A), P["leafL"])):
        for s in (+1, -1):
            lo, hi = _frame_box(fr_fn(s, P), sd_ar(s), (-9, L + 3), (-1, 8))
            xh = max(xh, -lo[0] + 2, hi[0] + 2, 28.0 if fr_fn is ant_frame else 0.0)
            ylo, yhi = min(ylo, lo[1] - 2), max(yhi, hi[1] + 2)
            zhi = max(zhi, hi[2] + 2)
    return float(xh), float(ylo), float(yhi), float(zhi)


def body_field(par=None, vox=0.35, sockets=False, fuse_ant=False, leaf=True):
    """pole korpusu: zebra + (gniazda poroza | poroze przytopione) + boczne uszy-liscie przytopione"""
    from build_figurki import add_local
    P = par or params()
    xh, ylo, yhi, zhi = extents(P)
    axes, (X, Y, Z) = make_grid(-xh, xh, ylo, yhi, -1.0, zhi, vox)
    F = SH.bunny_F(X, Y, Z, P)
    G = antler_geom(P["antLv"], P["antSp"], P["antTine"], P["antAng"], P["antS"])
    if sockets:
        for s in (+1, -1):
            a, b, c = ant_frame(s, P).to_local(X, Y, Z)
            F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
    if fuse_ant:
        for s in (+1, -1):
            fn = part_fn(ant_part(s < 0, P), None, peg=False, plate_b0=-4.5)
            F = add_local(F, axes, ant_frame(s, P), fn, a_rng=ant_ar(s, P), b_rng=(-9, G["Lc"] + 3), c_rng=(-1, 8))
    if leaf:
        A = P["leafW"] / 2 + 2
        for s in (+1, -1):
            fn = part_fn(leaf_part(P), None, peg=False, plate_b0=-4.5)
            F = add_local(F, axes, leaf_frame(s, P), fn, a_rng=(-A, A), b_rng=(-9, P["leafL"] + 3), c_rng=(-1, 8))
    return axes, F


# =====================================================================================================
# BUDOWA STL + KONTROLA STANDARDU
# =====================================================================================================
SIDES = ((+1, "prawe", "ear_R"), (-1, "lewe", "ear_L"))


def build(vox=0.35, par=None):
    P = par or params()
    KREG = make_model(P)
    G = antler_geom(P["antLv"], P["antSp"], P["antTine"], P["antAng"], P["antS"])
    t0 = time.time()
    print(f"renifer kregiel: H {KREG.H:.1f}, P0 poroza {KREG.ports['ear_R'].P0.round(2)}, N zeber {int(round(P['ribs']))}, poziomow poroza {G['levels']}")
    # --- calosc (poroze i uszy przytopione)
    axes, F = body_field(P, vox, fuse_ant=True)
    m_all = mesh_from_F(F, axes, vox)
    emit(m_all, "renifer_kregiel_calosc.stl", True, "poroze i uszy-liscie przytopione, jeden wydruk", style="rb")
    print(f"  calosc: {len(m_all.faces)} tr., {m_all.bounds[1] - m_all.bounds[0]}  ({time.time() - t0:.0f} s)")
    # --- korpus z gniazdami (uszy-liscie przytopione) + poroza wymienne przyciete do koperty
    axes, F = body_field(P, vox, sockets=True)
    m_body = mesh_from_F(F, axes, vox)
    emit(m_body, "renifer_kregiel_korpus.stl", True, "2 gniazda na poroze 5,4x5,4x9; uszy-liscie przytopione", style="rb", ports=list(KREG.ports.values()))
    parts = {}
    for s, nm, pn in SIDES:
        fp = ant_part(s < 0, P)
        m = part_mesh(fp, rb_trims([(KREG, pn)]), True, ant_ar(s, P), (-9, G["Lc"] + 3), 0.2)
        emit(m, f"renifer_kregiel_poroze_{nm}.stl", False, "druk na plecach; czop 5x5x8", style="rb")
        parts[f"renifer_kregiel_poroze_{nm}.stl"] = dict(mesh=trimesh.load(os.path.join(OUT, f"renifer_kregiel_poroze_{nm}.stl")), port=pn)
    print("== verify_set (korpus bez uszu-lisci + poroza) ==")
    n_pass, bad = verify_standard(P, vox)
    print(f"czas {time.time() - t0:.0f} s")
    return n_pass, bad


def verify_standard(par=None, vox=0.35, log=print):
    """kontrola wg STANDARD v1.0 (verify_set): gole korpus z gniazdami (bez uszu-lisci: koperta modelu jest bryla obrotowa) zbudowany w pamieci
    + poroza wczytane z out/. Wymaga wczesniej zbudowanych renifer_kregiel_poroze_*.stl (build)."""
    P = par or params()
    KREG = make_model(P)
    axes, F = body_field(P, vox, sockets=True, leaf=False)
    bare = mesh_from_F(F, axes, vox)
    parts = {f"renifer_kregiel_poroze_{nm}.stl": dict(mesh=trimesh.load(os.path.join(OUT, f"renifer_kregiel_poroze_{nm}.stl")), port=pn) for s, nm, pn in SIDES}
    bodies = {"renifer_kregiel_korpus.stl": dict(mesh=bare, ports=["ear_R", "ear_L"])}
    return verify_set(KREG, bodies, parts, rib_z=[("renifer_kregiel_korpus.stl", 40.0, int(round(P["ribs"])))], log=log)


if __name__ == "__main__":
    vox = float(sys.argv[1]) if len(sys.argv) > 1 else 0.35
    n_pass, bad = build(vox)
    sys.exit(1 if bad else 0)
