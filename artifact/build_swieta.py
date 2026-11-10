"""Sklada artefakt „Swiateczne dodatki”: artifact/swieta.src.html + swieta_core.js + swieta_outlines.json + fonts/Poppins-Bold-subset.ttf -> artifact/swieta.page.html
(biblioteki three, clipper-lib, opentype.js, earcut ladowane z jsDelivr w tagach <script>; wszystko inne jest wbudowane w strone).
  python3 artifact/build_swieta.py     (obrysy: python3 foremki_piernik.py --json)"""
import os, sys, json, base64
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
src = open(os.path.join(HERE, "swieta.src.html"), encoding="utf-8").read()
core = open(os.path.join(HERE, "swieta_core.js"), encoding="utf-8").read()
outl = open(os.path.join(HERE, "swieta_outlines.json"), encoding="utf-8").read()
font = base64.b64encode(open(os.path.join(ROOT, "fonts", "Poppins-Bold-subset.ttf"), "rb").read()).decode()
assert "</script" not in core and "/*__CORE__*/" in src and "/*__OUTLINES__*/ null" in src and "/*__FONT_B64__*/" in src
page = src.replace("/*__CORE__*/", core).replace("/*__OUTLINES__*/ null", outl).replace("/*__FONT_B64__*/", font)
open(os.path.join(HERE, "swieta.page.html"), "w", encoding="utf-8").write(page)
print(f"artifact/swieta.page.html: {len(page) / 1024:.0f} KB")
