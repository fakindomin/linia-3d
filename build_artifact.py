"""line.json (STANDARD, z export_line_json.py) + artifact/zebrowana_kolekcja.src.html -> artifact/zebrowana_kolekcja.html (podglad / edytor w przegladarce).

Zrodlowy HTML (.src.html) to wersja podgladu sprzed konsolidacji; ten skrypt NIE edytuje go recznie, tylko nakłada na niego lacki:
  * stale (czop, gniazdo, GAP, pitch zeber, nachylenie sufitu jajka 52 st.) i domyslne parametry krolika / jajka z line.json,
  * dynia i balwan jako modele 'line' (profil, pasma zeber i porty z line.json, artifact/line_core.js) zamiast przyblizen,
  * znacznik STANDARD vX.Y w naglowku i panel 'Standard linii'.
Kazda podmiana jest wymagana dokladnie raz (assert) - gdy zrodlo sie zmieni, skrypt przerwie zamiast po cichu pominac lacke.

Uzycie:  python export_line_json.py && python build_artifact.py        (wynik: artifact/zebrowana_kolekcja.html)
"""
import os, sys, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifact")
src = open(os.path.join(ART, "zebrowana_kolekcja.src.html"), encoding="utf8").read()
LINE = json.load(open(os.path.join(HERE, "line.json"), encoding="utf8"))
core_js = open(os.path.join(ART, "line_core.js"), encoding="utf8").read()


def sub1(s, old, new, label):
    n = s.count(old)
    assert n == 1, f"lacka '{label}': wzorzec wystepuje {n} razy (oczekiwano 1)"
    return s.replace(old, new)


def cut_between(s, start, end, label, keep_end=True):
    a = s.index(start)
    b = s.index(end, a)
    return s[:a] + (s[b:] if keep_end else s[b + len(end):])


h = src

# 1. dane linii na poczatku rdzenia
line_json = json.dumps(LINE, ensure_ascii=False, separators=(",", ":"))
h = sub1(h, "/*CORE_START*/", "/*CORE_START*/\n/* STANDARD v%s: dane z line.json (export_line_json.py); nie edytowac recznie */\nconst LINE=%s;" % (LINE["version"], line_json), "LINE")

# 2. stale uchwytow, rozstaw zeber
h = sub1(h, "const PEG_W=5,PEG_L=8,PEG_R=1,SOCK_W=5.4,SOCK_D=9,SOCK_R=1.25,Y0=0.25,GAP=0.3;",
         "const PEG_W=LINE.const.PEG_W,PEG_L=LINE.const.PEG_L,PEG_R=LINE.const.PEG_R,SOCK_W=LINE.const.SOCK_W,SOCK_D=LINE.const.SOCK_D,"
         "SOCK_R=LINE.const.SOCK_R,Y0=LINE.const.EAR_Y,GAP=LINE.const.GAP;", "uchwyty")
h = sub1(h, "const nRibs=r=>Math.round(2*Math.PI*r/3.4);", "const nRibs=r=>Math.round(2*Math.PI*r/LINE.const.RIB_PITCH);", "nRibs")

# 3. jajko: sufit wnek wg standardu (|dr/dz| <= LP_SLOPE, 52 st.), promien plaskiego sufitu
h = sub1(h, "E.cone=1/Math.tan(35*D2R);", "E.cone=LINE.models.jajko.cone.slope;", "stozek sufitu")
h = sub1(h, "ceil:P.ceilZ,Rtop:5,", "ceil:P.ceilZ,Rtop:LINE.models.jajko.cone.R_TOP,", "Rtop")

# 4. domyslne parametry krolika / jajka z line.json
h = sub1(h, "const RIBS={ribs:36,ribDepth:1.6,ribPow:.8};",
         "const RIBS={ribs:LINE.models.krolik.params.ribs,ribDepth:LINE.models.krolik.params.ribDepth,ribPow:LINE.models.krolik.params.ribPow};", "RIBS")
h = sub1(h, "const BUN={bodyW:38,bodyHz:52,bodyN:2.5,headR:16,headZ:105,blend:20,earTilt:14,earX:6,earT:5.5,ringH:.7,detach:0,explode:0};",
         "const BUN=Object.assign({},LINE.models.krolik.params,{earT:5.5,ringH:.7,detach:0,explode:0});", "BUN")
h = sub1(h, "const EGG_REF={W:56,H:89.5,NL:2.2,NU:1.9};",
         "const EGG_REF={W:LINE.models.jajko.params.eggW,H:LINE.models.jajko.params.eggH,NL:2.2,NU:1.9};", "EGG_REF")
h = sub1(h, "const EGGD={eggW:56,eggH:89.5,eggZ:34,eggNL:2.2,eggNU:1.9,seam:34,cavR:24,floor:4.5,lipH:7,wallCup:3.3,ceilZ:76,ribs:48,ribDepth:1.6,ribPow:.8,explode:30,earTilt:14,earX:6,earT:5.5,ringH:.7,earL:30.9,earW:14,ears:0};",
         "const EGGD=Object.assign({},LINE.models.jajko.params,{eggZ:LINE.models.jajko.params.seam,eggNL:EGG_REF.NL,eggNU:EGG_REF.NU,explode:30,earT:5.5,ringH:.7,earL:30.9,earW:14,ears:0});", "EGGD")

# 5. dynia i balwan: modele 'line'
h = sub1(h, "/* ===== definicje modeli ===== */", core_js + "\n/* ===== definicje modeli ===== */", "line_core")
dyn_old = re.search(r"  dynia:\{n:'Dynia'.*\n  balwan:\{n:'Bałwan'.*\n", h)
assert dyn_old, "brak wpisow dynia/balwan w M"
dyn_new = (
    "  dynia:{n:'Dynia',desc:'Szeroka, spłaszczona bryła 100 × 65 mm (bez ogonka) z gniazdem i wymiennym ogonkiem. Szerokość i wysokość ustawiasz osobno, żebra zachowują rozstaw 3,4 mm.',"
    "f:{real:1,kind:'line'},g:['lineBodyWH','lineRib','lineParts'],files:['korpus','ogonek'],d:{width:lineW0('dynia'),height:LINE.models.dynia.H,ribDepth:1.6,ribPow:.8,explode:0}},\n"
    "  balwan:{n:'Bałwan',desc:'Trzy żebrowane kule z kapeluszem w jednej bryle, gniazda na nos i miotłę. Profil, żebra (52 / 42 / 32 / 24) i porty z linii; "
    "w podglądzie jest nos, miotła tylko w skryptach.',"
    "f:{real:1,kind:'line'},g:['lineBody','lineRib','lineParts'],files:['korpus','nos'],d:{scale:1,ribDepth:1.6,ribPow:.8,explode:0}}\n")
h = h[:dyn_old.start()] + dyn_new + h[dyn_old.end():]

# martwy kod po zmianie: buildOld / profFromR / BASE
h = cut_between(h, "function profFromR(", "function buildModel(", "buildOld")
h = sub1(h, "function buildModel(id,P,opt){opt=opt||{};return M[id].f.real?buildReal(id,P,opt):buildOld(id,P,opt);}",
         "function buildModel(id,P,opt){opt=opt||{};return buildReal(id,P,opt);}", "buildModel")
h = sub1(h, "const BASE={height:100,width:70,egg:.12,full:1,flat:.06,ribs:36,ribDepth:1.6,ribShape:1,explode:0};\n", "", "BASE")
h = sub1(h, "const defaults=id=>Object.assign({},M[id].old?BASE:{},M[id].d);", "const defaults=id=>Object.assign({},M[id].d);", "defaults")
h = sub1(h, "  if(F.kind==='egg')return buildEgg(id,P,vox,ex,parts,warn,opt);",
         "  if(F.kind==='line')return buildLine(id,P,vox,ex,parts,warn);\n  if(F.kind==='egg')return buildEgg(id,P,vox,ex,parts,warn,opt);", "dispatch")
h = sub1(h, "  const F=M[id].f;\n  if(F.kind==='egg'&&F.real)return[id+'_miseczka.stl',id+'_czapka.stl'];",
         "  const F=M[id].f;\n  if(F.kind==='line')return M[id].files.map(s=>id+'_'+s+'.stl');\n  if(F.kind==='egg'&&F.real)return[id+'_miseczka.stl',id+'_czapka.stl'];", "fileNames")

# 6. grupy suwakow: nowe dla modeli 'line', usuniete stare (body, snow, snowhat, ribsOld, stem, nose)
h = sub1(h, "const GR={\n",
         "const GR={\n"
         "  lineBody:{t:'Bryła',items:[{k:'scale',l:'Skala bryły (żebra zachowują rozstaw)',min:.5,max:1.5,step:.01,f:'pct'}]},\n"
         "  lineBodyWH:{t:'Bryła',items:[\n"
         "    {k:'width',l:'Szerokość (po grzbietach żeber)',min:60,max:140,step:.5,f:'mm'},\n"
         "    {k:'height',l:'Wysokość bryły (bez ogonka)',min:40,max:100,step:.5,f:'mm'}]},\n"
         "  lineRib:{t:'Żebra',items:[\n"
         "    {k:'ribDepth',l:'Głębokość rowków (łącznie)',min:0,max:3.2,step:.1,f:'mm'},\n"
         "    {k:'ribPow',l:'Ostrość żeber (mniej = ostrzejsze)',min:.3,max:1.6,step:.05,f:'num'}]},\n"
         "  lineParts:{t:'Podgląd',items:[{k:'explode',l:'Rozsunięcie dodatków w podglądzie',min:0,max:60,step:1,f:'mm'}]},\n", "GR")
h = cut_between(h, "  body:{t:'Bryła',items:[\n    {k:'height'", "};\nconst groupsFor", "grupy body..nose")

# 6b. jajko: prog ostrzezenia o scianie czapki. Rekomendowana konstrukcja (lip R_LIP + 0,25 luzu) ma przy ksztalcie 1,4 mm (2,2 promieniowo - rowek 0,8),
#     czyli 3 sciezki dyszy 0,4: domyslny model nie moze swiecic ostrzezeniem
h = sub1(h, "else if(wp<1.6)warn.push('Ścianka czapki ma ", "else if(wp<1.2)warn.push('Ścianka czapki ma ", "prog scianki czapki")

# 6c. zakladka Zapis: rola siatek z podgladu
h = sub1(h, "Zapisują się aktualne ustawienia suwaków.", "Zapisują się aktualne ustawienia suwaków. To siatki robocze z podglądu; pliki do druku powstają ze skryptów Pythona (STANDARD v%s)." % LINE["version"], "opis zapisu")

# 7. naglowek: znacznik STANDARD i panel 'Standard linii'
h = sub1(h, '<p class="mdesc">Narzędzia, które pilnują, żeby wszystkie modele były jedną serią.</p></div>\n      <div class="btnrow">',
         '<p class="mdesc">Narzędzia, które pilnują, żeby wszystkie modele były jedną serią.</p></div>\n'
         '      <div class="group"><h2>Standard linii</h2><p id="stdInfo"></p></div>\n      <div class="btnrow">', "panel standardu")
h = sub1(h, "const TABS=['sliders','save','line'];",
         "function stdBanner(){\n"
         "  const c=LINE.const,m=LINE.peg_socket_clearance,f=x=>String(x).replace('.',',');\n"
         "  $('.sub').textContent=ORDER.length+' modeli · STANDARD v'+LINE.version+' · wymiary w milimetrach';\n"
         "  $('#stdInfo').textContent='Wersja '+LINE.version+' (źródła '+LINE.source_sha1+'). Czop '+c.PEG_W+'×'+c.PEG_W+'×'+c.PEG_L+', gniazdo '+f(c.SOCK_W)+'×'+f(c.SOCK_W)+'×'+c.SOCK_D+"
         "', luz czop–gniazdo od '+f(Math.min(...Object.values(m)))+' mm. Żebra ±'+f(c.RIB_AMP)+' mm, rozstaw '+f(c.RIB_PITCH)+' mm. Sufity wnęk nie bardziej niż '+Math.round(Math.atan(c.LP_SLOPE)*180/Math.PI)+"
         "'° od pionu. Dynia i bałwan mają profil i żebra z tego samego pliku co skrypty Pythona.';\n}\n"
         "const TABS=['sliders','save','line'];", "stdBanner")
h = sub1(h, "renderChips();renderControls();rebuild(false);renderQual();", "stdBanner();renderChips();renderControls();rebuild(false);renderQual();", "boot")

out = os.path.join(ART, "zebrowana_kolekcja.html")
open(out, "w", encoding="utf8").write(h)
print(f"{out}: {len(h) / 1024:.0f} kB (zrodlo {len(src) / 1024:.0f} kB), STANDARD v{LINE['version']} / {LINE['source_sha1']}")

# wersja do publikacji (Artifact opakowuje strone we wlasny szkielet <!doctype><head><body>): sama tresc od <title> do konca <script>
m = re.match(r"<!doctype html><html><head>.*?</head><body>\n?", h, re.S)
assert m, "brak szkieletu na poczatku zrodla"
page = h[m.end():]
page = re.sub(r"\s*</body></html>\s*$", "\n", page)
assert page.lstrip().startswith("<title>") and "<html" not in page[:400]
pub = os.path.join(ART, "zebrowana_kolekcja.page.html")
open(pub, "w", encoding="utf8").write(page)
print(f"{pub}: {len(page) / 1024:.0f} kB (do publikacji w Artifact)")
