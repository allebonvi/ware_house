import re
from pathlib import Path

# Path default (modifica se serve)
p = Path("./layout_window.py")
if not p.exists():
    raise SystemExit(f"File non trovato: {p}")

src = p.read_text(encoding="utf-8")

# 1) Rimuovi i parametri border_color="transparent" nelle chiamate configure(...).
#    Gestiamo i casi ", border_color='transparent'" e "border_color='transparent',"
patterns = [
    re.compile(r""",\s*border_color\s*=\s*["']transparent["']"""),  # , border_color="transparent"
    re.compile(r"""border_color\s*=\s*["']transparent["']\s*,\s*""") # border_color="transparent",
]
for pat in patterns:
    src = pat.sub("", src)

# 2) Se sono rimaste virgole prima della parentesi di chiusura:  ",   )" -> ")"
src = re.sub(r",\s*\)", ")", src)

# 3) (opzionale/robusto) Rimuovi border_color=None se presente in qualche versione
patterns_none = [
    re.compile(r""",\s*border_color\s*=\s*None"""),
    re.compile(r"""border_color\s*=\s*None\s*,\s*""")
]
for pat in patterns_none:
    src = pat.sub("", src)
src = re.sub(r",\s*\)", ")", src)

# 4) NOTE: manteniamo eventuali border_color="blue" per l’highlight

# Scrivi backup e nuovo file
bak = p.with_suffix(".py.bak_fix_bc_transparent")
if not bak.exists():
    bak.write_text(Path(p).read_text(encoding="utf-8"), encoding="utf-8")

p.write_text(src, encoding="utf-8")
print(f"Patch applicata a {p}. Backup: {bak}")
