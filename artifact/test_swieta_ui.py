"""Test strony artefaktu „Swiateczne dodatki” w Chromium (Playwright): bez bledow konsoli, podglad 3D sie rysuje, wpisanie imienia buduje etykiete, suwaki zmieniaja model,
pobranie zwraca ZIP ze szczelnym STL o oczekiwanej objetosci. Biblioteki CDN sa podmieniane lokalnymi z artifact/node_modules (npm install w artifact/).
  python3 artifact/test_swieta_ui.py [--shots DIR]        # zrzuty ekranu (telefon 390 x 844 i pulpit) do DIR"""
import os, sys, io, json, base64, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import numpy as np, trimesh
from playwright.sync_api import sync_playwright
shots = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else None
if shots: os.makedirs(shots, exist_ok=True)
NM = os.path.join(HERE, "node_modules")
LOCAL = {"three@0.128.0/build/three.min.js": "three/build/three.min.js", "clipper-lib@6.4.2/clipper.js": "clipper-lib/clipper.js",
         "opentype.js@1.3.4/dist/opentype.min.js": "opentype.js/dist/opentype.min.js", "earcut@2.2.4/dist/earcut.min.js": "earcut/dist/earcut.min.js"}
page_html = open(os.path.join(HERE, "swieta.page.html"), encoding="utf-8").read()
doc = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>'
       ':root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + page_html + '</body></html>')
MOCK = """window.__saved = null; window.claude = { use: async (n) => n === 'downloads' ? { save: async (r) => { const b = new Uint8Array(r.data); let s = ''; for (let i = 0; i < b.length; i++) s += String.fromCharCode(b[i]); window.__saved = { filename: r.filename, b64: btoa(s) }; return { status: 'saved' }; } } : null };"""
errs, bad = [], 0


def check(cond, msg):
    global bad
    print(("PASS  " if cond else "FAIL  ") + msg); bad += (not cond)


def route(r):
    u = r.request.url
    for k, v in LOCAL.items():
        if k in u:
            return r.fulfill(path=os.path.join(NM, v), content_type="application/javascript")
    if "fonts.googleapis.com" in u or "fonts.gstatic.com" in u:
        return r.fulfill(body="", content_type="text/css")
    if u.startswith("data:") or u.startswith("about:") or u.startswith("blob:"):
        return r.continue_()
    return r.abort()


def stl_from_saved(page):
    sv = page.evaluate("window.__saved")
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(sv["b64"])))
    assert z.testzip() is None and len(z.namelist()) == 1
    name = z.namelist()[0]
    m = trimesh.load(io.BytesIO(z.read(name)), file_type="stl")
    return sv["filename"], name, m


with sync_playwright() as p:
    br = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    for label, vp, dsf in (("phone", {"width": 390, "height": 844}, 2), ("desktop", {"width": 1100, "height": 900}, 1)):
        ctx = br.new_context(viewport=vp, device_scale_factor=dsf, has_touch=(label == "phone"))
        ctx.add_init_script(MOCK)
        pg = ctx.new_page()
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
        pg.route("**/*", route)
        pg.set_content(doc, wait_until="load")
        pg.wait_for_function("window.__swieta && window.__swieta.cur()", timeout=20000)
        check(pg.evaluate("!!window.__viewer"), f"[{label}] podglad 3D (WebGL) uruchomiony")
        check(not pg.evaluate("document.getElementById('stage').classList.contains('err')"), f"[{label}] brak komunikatu bledu podgladu")
        check(pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"[{label}] brak poziomego przewijania strony")
        # --- etykieta
        check(pg.is_disabled("#dl"), f"[{label}] przycisk pobierania wylaczony bez imienia")
        pg.fill("#name", "Zosia")
        pg.wait_for_function("window.__swieta.cur() && window.__swieta.cur().stl === 'etykieta_zosia.stl'")
        check(pg.is_enabled("#dl"), f"[{label}] przycisk wlaczony po wpisaniu imienia")
        if shots: pg.screenshot(path=f"{shots}/{label}_etykieta.png", full_page=True)
        pg.fill("#name", "Łukasz Żółć")
        pg.wait_for_function("window.__swieta.cur().stl === 'etykieta_lukasz_zolc.stl'")
        pg.click("#dl"); pg.wait_for_function("window.__saved !== null", timeout=15000)
        fn, inner, m = stl_from_saved(pg)
        import etykieta as ET
        ref, _ = ET.build_label("Łukasz Żółć", 11.0)
        check(fn == "etykieta_dla_lukasz_zolc.zip" and inner == "etykieta_lukasz_zolc.stl", f"[{label}] nazwy plikow: {fn} / {inner}")
        check(m.is_watertight and abs(m.volume - ref.volume) / ref.volume < 0.003, f"[{label}] STL z ZIP: szczelny, V {m.volume:.0f} vs Python {ref.volume:.0f}")
        pg.evaluate("window.__saved = null")
        # --- czubek
        pg.click("#tab-czubek"); pg.wait_for_function("window.__swieta.cur() && window.__swieta.cur().kind === 'czubek'", timeout=20000)
        pg.fill("#top", "14") if False else pg.evaluate("(()=>{const e=document.getElementById('top'); e.value='14'; e.dispatchEvent(new Event('input',{bubbles:true}));})()")
        pg.wait_for_function("window.__swieta.cur().info.geo && Math.abs(window.__swieta.cur().info.geo.r_h*2 - 14.6) < 0.01", timeout=20000)
        if shots: pg.screenshot(path=f"{shots}/{label}_czubek.png", full_page=True)
        pg.click("#chip-sec"); pg.click("#chip-view")
        pg.click("#dl"); pg.wait_for_function("window.__saved !== null", timeout=20000)
        fn, inner, m = stl_from_saved(pg)
        import czubek_choinkowy as CZ
        rm, g, M = CZ.build(14, 200, 62)
        check(m.is_watertight and abs(m.volume - rm.volume) / rm.volume < 0.003 and len(m.split(only_watertight=False)) == 1, f"[{label}] czubek: {fn}, V {m.volume:.0f} vs Python {rm.volume:.0f}, szczelny, 1 czesc")
        pg.evaluate("window.__saved = null")
        # --- foremki
        pg.click("#tab-foremki"); pg.wait_for_function("window.__swieta.cur() && window.__swieta.cur().kind === 'foremki'", timeout=20000)
        pg.click("#shapes button[data-k=renifer]")
        pg.evaluate("(()=>{for (const [id,v] of [['flw','8'],['flt','3']]) { const e=document.getElementById(id); e.value=v; e.dispatchEvent(new Event('input',{bubbles:true})); }})()")
        pg.wait_for_function("window.__swieta.cur().stl === 'foremka_renifer.stl' && window.__swieta.cur().zip.includes('k8_0x3_0')", timeout=20000)
        pg.wait_for_timeout(500)
        if shots: pg.screenshot(path=f"{shots}/{label}_foremki.png", full_page=True)
        pg.click("#dl"); pg.wait_for_function("window.__saved !== null", timeout=20000)
        fn, inner, m = stl_from_saved(pg)
        import foremki_piernik as FP
        FP.FL_W, FP.FL_T = 8.0, 3.0
        rf = FP.cutter(FP.dough("renifer")); FP.FL_W, FP.FL_T = 5.0, 2.0
        check(m.is_watertight and abs(m.volume - rf.volume) / rf.volume < 0.006, f"[{label}] foremka: {fn}, V {m.volume:.0f} vs Python {rf.volume:.0f}, szczelna")
        ctx.close()
    br.close()
real = [e for e in errs if "favicon" not in e and "ERR_FAILED" not in e and "net::" not in e and "Failed to load resource" not in e and "document.write" not in e]
check(not real, "brak bledow konsoli" + (": " + " | ".join(real[:4]) if real else ""))
print("OK" if not bad else f"BLEDY: {bad}")
sys.exit(1 if bad else 0)
