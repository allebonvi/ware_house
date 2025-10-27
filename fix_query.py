from pathlib import Path
import re

p = Path("./layout_window.py")
src = p.read_text(encoding="utf-8")

backup = p.with_suffix(".py.bak_perf")
if not backup.exists():
    backup.write_text(src, encoding="utf-8")

# 1) Rimuovi il bind su <Configure> che innescava refresh continui.
src = src.replace(
    '        self.bind("<Configure>", lambda e: self.after_idle(self._refresh_stats))\n',
    '        # disabilitato: il refresh ad ogni <Configure> generava molte query/lag\n'
    '        # self.bind("<Configure>", lambda e: self.after_idle(self._refresh_stats))\n'
)

# 2) Nel metodo _refresh_stats, elimina il blocco che interroga il DB "globale".
#    Riconosciamo il blocco su "sql_tot = ..." e lo neutralizziamo.
src = re.sub(
    r"\n\s*# globale dal DB[\s\S]*?self\._async\.run\(.*?\)\)\n",
    "\n        # [patch] rimosso refresh globale da DB: calcoliamo solo dalla matrice in memoria\n",
    src,
    flags=re.MULTILINE
)

# 3) Aggiungi un flag di vita finestra e un destroy sicuro
#    - settiamo self._alive = True in __init__
#    - override destroy() per annullare timer e marcare _alive=False
src = src.replace(
    "        self._last_req = 0\n",
    "        self._last_req = 0\n"
    "        self._alive = True\n"
    "        self._stats_after_id = None  # se mai userai un refresh periodico, potremo cancellarlo qui\n"
)

# aggiungi metodo destroy() se non esiste già
if "def destroy(self):" not in src:
    insert_point = src.find("def open_layout_window(")
    destroy_method = (
        "\n    def destroy(self):\n"
        "        # evita nuovi refresh/async dopo destroy\n"
        "        self._alive = False\n"
        "        # cancella eventuali timer\n"
        "        try:\n"
        "            if self._stats_after_id is not None:\n"
        "                self.after_cancel(self._stats_after_id)\n"
        "        except Exception:\n"
        "            pass\n"
        "        # pulizia UI leggera\n"
        "        try:\n"
        "            for w in list(self.host.winfo_children()):\n"
        "                w.destroy()\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            super().destroy()\n"
        "        except Exception:\n"
        "            pass\n\n"
    )
    src = src[:insert_point] + destroy_method + src[insert_point:]

# 4) Nei callback _ok/_err delle query, assicurati che non facciano nulla se la finestra è chiusa
#    => sostituiamo 'def _ok(res):' con un guard iniziale e idem per _err.
src = re.sub(
    r"def _ok\(res\):\n",
    "def _ok(res):\n"
    "            if not getattr(self, '_alive', True) or not self.winfo_exists():\n"
    "                return\n",
    src
)
src = re.sub(
    r"def _err\(ex\):\n",
    "def _err(ex):\n"
    "            if not getattr(self, '_alive', True) or not self.winfo_exists():\n"
    "                return\n",
    src
)

# 5) Piccola robustezza: prima di schedulare highlight post-ricarica controlla ancora _alive
src = src.replace(
    "        if self._pending_focus and self._pending_focus[0] == corsia:\n",
    "        if getattr(self, '_alive', True) and self._pending_focus and self._pending_focus[0] == corsia:\n"
)

p.write_text(src, encoding="utf-8")
print(f"Patch applicata a {p} (backup in {backup}).")
