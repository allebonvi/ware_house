"""
Entry point principale per il launcher Warehouse.

Questo modulo configura un singolo loop asyncio, crea un client DB asincrono
condiviso e mostra una finestra di avvio CustomTkinter che apre gli strumenti
(layout, reset corsie, ricerca UDC e picking list).
"""

import sys  # Libreria standard: info piattaforma e runtime.
import asyncio  # Libreria standard: gestione event loop asincrono.
import tkinter as tk  # Libreria standard: widget base Tk e tipi.
import customtkinter as ctk  # Terze parti: widget Tk a tema.

from async_msssql_query import AsyncMSSQLClient, make_mssql_dsn  # Client DB async e builder DSN.
from async_loop_singleton import get_global_loop  # Loop asyncio condiviso (thread in background).

from layout_window import open_layout_window  # Apre la finestra layout corsie.
from view_celle_multiple import open_celle_multiple_window  # Apre la finestra celle con piu UDC.
from reset_corsie import open_reset_corsie_window  # Apre la finestra reset corsie.
from search_pallets import open_search_window  # Apre la finestra ricerca UDC/lotto/codice.

# Prova factory, altrimenti frame, altrimenti app (senza passare conn_str all'app).
try:
    from gestione_pickinglist import create_frame as create_pickinglist_frame  # Factory preferita.
except Exception:
    try:
        from gestione_pickinglist import GestionePickingListFrame as _PLFrame  # Export solo frame.
        import customtkinter as ctk  # Import locale per il fallback.

        def create_pickinglist_frame(parent, db_client=None, conn_str=None):
            """Factory wrapper per creare il frame picking list con client DB."""
            ctk.set_appearance_mode("light")  # Mantiene coerente la modalita UI.
            ctk.set_default_color_theme("green")  # Usa il tema verde in tutta l'app.
            return _PLFrame(parent, db_client=db_client, conn_str=conn_str)  # Ritorna il frame.
    except Exception:
        # Ultimo fallback: alcune versioni espongono solo la App e NON accettano parametri.
        from gestione_pickinglist import GestionePickingListApp as _PLApp  # Export solo app.

        def create_pickinglist_frame(parent, db_client=None, conn_str=None):
            """Fallback per avviare l'app picking list senza parametri."""
            app = _PLApp()  # Avvia l'app senza parametri.
            app.mainloop()  # Esegue il suo main loop.
            return tk.Frame(parent)  # Ritorna un frame fittizio per compatibilita.

# ---- Config ----
SERVER = r"mde3\gesterp"  # SQL Server host\instance.
DBNAME = "Mediseawall"  # Nome database di default.
USER = "sa"  # Utente SQL Server.
PASSWORD = "1Password1"  # Password SQL Server.

if sys.platform.startswith("win"):
    # Windows: forza SelectorEventLoopPolicy per compatibilita aiodbc.
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# Crea UN solo loop globale e rendilo il default ovunque.
_loop = get_global_loop()
asyncio.set_event_loop(_loop)

# --- Compatibilita DPI tracker ---
def _noop(*args, **kwargs):
    """No-op per metodi Tk mancanti su alcune piattaforme."""
    return None

if not hasattr(tk.Toplevel, "block_update_dimensions_event"):
    tk.Toplevel.block_update_dimensions_event = _noop  # type: ignore[attr-defined]
if not hasattr(tk.Toplevel, "unblock_update_dimensions_event"):
    tk.Toplevel.unblock_update_dimensions_event = _noop  # type: ignore[attr-defined]

dsn_app = make_mssql_dsn(server=SERVER, database=DBNAME, user=USER, password=PASSWORD)
db_app = AsyncMSSQLClient(dsn_app)

def open_pickinglist_window(parent: tk.Misc, db_client: AsyncMSSQLClient):
    """Crea e mostra la finestra picking list con reveal senza sfarfallio."""
    win = ctk.CTkToplevel(parent)
    win.title("Gestione Picking List")
    win.geometry("1200x700+0+100")
    win.minsize(1000, 560)

    # 1) Tieni la toplevel nascosta mentre costruisci il contenuto.
    try:
        win.withdraw()
        # Opzionale: resta invisibile anche se il WM la mostra per un istante.
        win.attributes("-alpha", 0.0)
    except Exception:
        pass

    # 2) Costruisci il contenuto della finestra.
    frame = create_pickinglist_frame(win, db_client=db_client)
    try:
        frame.pack(fill="both", expand=True)
    except Exception:
        pass

    # 3) Mostra la finestra quando e pronta (senza topmost).
    try:
        win.update_idletasks()
        try:
            win.transient(parent)  # Mantiene lo z-order legato alla main.
        except Exception:
            pass
        try:
            win.deiconify()
        except Exception:
            pass
        win.lift()
        try:
            win.focus_force()
        except Exception:
            pass
        # Ripristina opacita.
        try:
            win.attributes("-alpha", 1.0)
        except Exception:
            pass
    except Exception:
        pass

    win.bind("<Escape>", lambda e: win.destroy())
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    return win

class Launcher(ctk.CTk):
    """Piccola finestra launcher che apre i tool dell'app."""
    def __init__(self):
        super().__init__()
        self.title("Warehouse 1.0.0")
        self.geometry("1200x70+0+0")

        wrap = ctk.CTkFrame(self)
        wrap.pack(pady=10, fill="x")

        ctk.CTkButton(
            wrap,
            text="Gestione Corsie",
            command=lambda: open_reset_corsie_window(self, db_app),
        ).grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(
            wrap,
            text="Gestione Layout",
            command=lambda: open_layout_window(self, db_app),
        ).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(
            wrap,
            text="UDC Fantasma",
            command=lambda: open_celle_multiple_window(self, db_app),
        ).grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(
            wrap,
            text="Ricerca UDC",
            command=lambda: open_search_window(self, db_app),
        ).grid(row=0, column=3, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(
            wrap,
            text="Gestione Picking List",
            command=lambda: open_pickinglist_window(self, db_app),
        ).grid(row=0, column=4, padx=6, pady=6, sticky="ew")

        for i in range(5):
            wrap.grid_columnconfigure(i, weight=1)

        def _on_close():
            """Rilascia il client DB async prima di chiudere il launcher."""
            try:
                fut = asyncio.run_coroutine_threadsafe(db_app.dispose(), _loop)
                try:
                    fut.result(timeout=2)
                except Exception:
                    pass
            finally:
                self.destroy()

        self.protocol("WM_DELETE_WINDOW", _on_close)

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    Launcher().mainloop()
