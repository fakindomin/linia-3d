"""Buduje WSZYSTKIE modele lowpoly linii wg STANDARD v1.0 (models.py + standard.py). Wyniki: out/lp_*.stl
 krolik/renifer: lp_korpus_bazowy, lp_krolik_calosc, lp_renifer_calosc, lp_ucho_{prawe,lewe}, lp_ucho_dlugie_{prawe,lewe}, lp_poroze_{prawe,lewe}
 jajko: lp_jajko_miseczka, lp_jajko_czapka_gniazda, lp_jajko_czapka_uszy, lp_jajko_czapka_uszy_dlugie
 dynia: lp_dynia_korpus, lp_dynia_korpus_platy, lp_dynia_ogonek
 balwan: lp_balwan, lp_balwan_nos, lp_balwan_miotla"""
import sys, time, pickle
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import *

T0 = time.time()
RES = {}


def put(name, m, upright=True, note="", ports=()):
    RES[name] = m
    emit(m, name + ".stl", upright=upright, note=note, style="lp", ports=ports)


# ---------- krolik / renifer ----------
body = lp_bunny_solid()
for pn, p in BUNNY.ports.items():
    print(f"krolik {pn}: odleglosc P0-powierzchnia {port_deviation(body, p):.2f} mm")
parts, info = lp_ear_parts()
print(f"uszy: L krotkie {info['L_SHORT']:.2f}, dlugie {L_LONG}, poroze lam {info['LAM']:.4f}")
for nm, m in parts.items():
    put(nm, m, upright=False, note="druk na plecach (plaska strona do stolu)")
put("lp_korpus_bazowy", cut_ports(body, BUNNY), note="2 gniazda 5,4x5,4x9, pochylone 14 st.", ports=list(BUNNY.ports.values()))
leaf_f = ear_leaf(info["L_SHORT"], -4.5)
ant_Rf = antler_solid(info["LAM"], b0=-4.5)
ant_Lf = mirror_a(ant_Rf)
fr = {s: BUNNY.ports[pn].frame for s, _, pn in SIDES}
put("lp_krolik_calosc", union(body, *[to_global(leaf_f, fr[s]) for s in (+1, -1)]))
put("lp_renifer_calosc", union(body, to_global(ant_Rf, fr[+1]), to_global(ant_Lf, fr[-1])))

# ---------- jajko ----------
egg, eg = lp_egg_parts()
for pn, p in EGG.ports.items():
    print(f"jajko {pn}: odleglosc P0-powierzchnia {port_deviation(eg['full'], p):.2f} mm")
notes = {"lp_jajko_miseczka": "otworem do gory", "lp_jajko_czapka_gniazda": "otworem do dolu (brzeg na stole), gniazda na uszy",
         "lp_jajko_czapka_uszy": "otworem do dolu; uszy przytopione", "lp_jajko_czapka_uszy_dlugie": "otworem do dolu; dlugie uszy przytopione"}
for nm, m in egg.items():
    put(nm, m, note=notes[nm], ports=list(EGG.ports.values()))

# ---------- dynia ----------
pk, pi = lp_pumpkin_parts()
print(f"dynia stem: odleglosc P0-powierzchnia {port_deviation(pi['sm'], PUMPKIN.ports['stem']):.2f} / {port_deviation(pi['lb'], PUMPKIN.ports['stem']):.2f} mm")
for nm, m in pk.items():
    put(nm, m, note="druk do gory nogami: koniec ogonka na stole" if nm.endswith("ogonek") else "", ports=list(PUMPKIN.ports.values()))

# ---------- balwan ----------
sn, si = lp_snowman_parts()
for pn, p in SNOWMAN.ports.items():
    print(f"balwan {pn}: odleglosc P0-powierzchnia {port_deviation(si['solid'], p):.2f} mm")
put("lp_balwan", sn["lp_balwan"], note="2 gniazda: nos (przod) i miotla (prawa strona, 55 st.)", ports=list(SNOWMAN.ports.values()))
put("lp_balwan_nos", sn["lp_balwan_nos"], upright=False, note="plaski spod na stole")
put("lp_balwan_miotla", sn["lp_balwan_miotla"], upright=False, note="druk na plasko")
pickle.dump(dict(bodies=dict(bunny=body, egg_full=eg["full"], pump_sm=pi["sm"], pump_lb=pi["lb"], snow=si["solid"]), res=RES), open(OUT + "/_lp_std.pkl", "wb"))
print(f"czas {time.time() - T0:.0f} s")
