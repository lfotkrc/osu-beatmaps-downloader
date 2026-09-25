#!/usr/bin/env python3
"""
osu! Beatmap Downloader — édition "futuriste"
-----------------------------------------------
Interface graphique moderne basée sur ttkbootstrap (le fork de tkinter avec
les thèmes type Bootstrap : sombre, néon, etc.), avec :
  - miniatures des covers de beatmaps
  - filtres de recherche (mode, statut, étoiles min, tri)
  - sélecteur de thème en direct
  - téléchargement .osz avec barre de progression par carte

Dépendances (légères) :
    pip install ttkbootstrap requests pillow

Lancer :
    python osu_downloader.py

Pour un .exe Windows autonome :
    pip install pyinstaller
    pyinstaller --onefile --windowed --name "osu-downloader" osu_downloader.py
"""

import io
import os
import threading
from pathlib import Path

import requests
from PIL import Image, ImageTk

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox

API_SEARCH = "https://api.nerinyan.moe/search"
API_DOWNLOAD = "https://api.nerinyan.moe/d/{id}"

# Certains hébergeurs (Cloudflare, ppy.sh...) bloquent les requêtes sans
# User-Agent "navigateur" -> on en met un partout pour éviter les 403 silencieux.
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 osu-downloader/1.0"
}

DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "osu_maps"
CARD_W, CARD_H = 260, 90          # taille des miniatures de cover
CARDS_PER_ROW = 2

MODES = {"Tous": None, "osu!": 0, "Taiko": 1, "Catch": 2, "Mania": 3}
STATUSES = {
    "Tous": None,
    "Ranked": "ranked",
    "Loved": "loved",
    "Qualified": "qualified",
    "Pending": "pending",
    "Graveyard": "graveyard",
    "WIP": "wip",
}
SORTS = {
    "Pertinence": "relevance",
    "Plus populaire": "favourites",
    "Récent": "updated",
    "Titre (A-Z)": "title",
}
# Thèmes ttkbootstrap au look "futuriste" en priorité, mais tous sont proposés
THEMES = ["cyborg", "vapor", "solar", "superhero", "darkly", "flatly", "cosmo", "minty"]


class BeatmapCard(tb.Frame):
    """Une carte affichant la cover, le titre et un bouton de téléchargement."""

    def __init__(self, master, app, data):
        super().__init__(master, bootstyle="dark", padding=8)
        self.app = app
        self.data = data
        self.photo = None  # garder une référence sinon l'image disparaît

        self.configure(relief="raised", borderwidth=1)

        self.cover_label = tb.Label(self, text="...", anchor="center",
                                     width=22, bootstyle="dark", font=("Segoe UI", 9))
        self.cover_label.grid(row=0, column=0, rowspan=3, padx=(0, 10), sticky="nsew")

        title = data.get("title_unicode") or data.get("title", "?")
        artist = data.get("artist_unicode") or data.get("artist", "?")
        creator = data.get("creator", "?")
        status = (data.get("status") or "?").capitalize()

        stars = [b.get("difficulty_rating", 0) for b in data.get("beatmaps", []) if b.get("difficulty_rating")]
        star_txt = f"★{min(stars):.1f} - {max(stars):.1f}" if stars else "★?"
        modes = sorted({b.get("mode", "") for b in data.get("beatmaps", [])})
        mode_txt = ", ".join(m for m in modes if m) or "?"

        tb.Label(self, text=title, font=("Segoe UI", 11, "bold"),
                  bootstyle="light", wraplength=280, anchor="w").grid(row=0, column=1, sticky="w")
        tb.Label(self, text=f"{artist}  —  mappé par {creator}", bootstyle="secondary",
                  wraplength=280, anchor="w").grid(row=1, column=1, sticky="w")
        tb.Label(self, text=f"{status}  •  {star_txt}  •  {mode_txt}",
                  bootstyle="info", anchor="w").grid(row=2, column=1, sticky="w")

        btn_frame = tb.Frame(self)
        btn_frame.grid(row=0, column=2, rowspan=3, padx=(10, 0), sticky="ns")
        self.dl_btn = tb.Button(btn_frame, text="⬇ Télécharger", bootstyle="success-outline",
                                 command=self.download)
        self.dl_btn.pack(fill="x")
        # La barre de progression n'est affichée que pendant un téléchargement,
        # pour éviter un rectangle gris vide en permanence sous le bouton.
        self.progress = tb.Progressbar(btn_frame, mode="determinate", bootstyle="success-striped")
        self.status_lbl = tb.Label(btn_frame, text="", bootstyle="secondary")
        self.status_lbl.pack()

        self.columnconfigure(1, weight=1)
        self.load_cover_async()

    # ---------- cover ----------

    def load_cover_async(self):
        covers = self.data.get("covers") or {}
        url = covers.get("list") or covers.get("card") or covers.get("cover")
        if not url:
            return
        threading.Thread(target=self._load_cover_worker, args=(url,), daemon=True).start()

    def _load_cover_worker(self, url):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img.thumbnail((CARD_W, CARD_H))
            # recadrage centré pour un format uniforme
            canvas = Image.new("RGB", (CARD_W, CARD_H), (30, 30, 30))
            x = (CARD_W - img.width) // 2
            y = (CARD_H - img.height) // 2
            canvas.paste(img, (x, y))
        except Exception:
            return
        self.after(0, lambda: self._set_cover(canvas))

    def _set_cover(self, pil_img):
        if not self.winfo_exists():
            return
        self.photo = ImageTk.PhotoImage(pil_img)
        self.cover_label.configure(image=self.photo, text="")

    # ---------- téléchargement ----------

    def download(self):
        self.dl_btn.configure(state="disabled")
        self.status_lbl.configure(text="En cours...")
        self.progress.configure(value=0)
        self.progress.pack(fill="x", pady=(6, 0), before=self.status_lbl)
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        set_id = self.data.get("id")
        artist = self.data.get("artist", "unknown")
        title = self.data.get("title", "unknown")
        safe_name = "".join(c for c in f"{artist} - {title}" if c not in '\\/:*?"<>|').strip()
        out_dir = Path(self.app.dir_var.get())
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{safe_name} [{set_id}].osz"

        url = API_DOWNLOAD.format(id=set_id)
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done = 0
                self.after(0, lambda: self.progress.configure(maximum=max(total, 1), value=0))
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        self.after(0, lambda d=done: self.progress.configure(value=d))
        except Exception as exc:
            self.after(0, lambda: self._done(False, str(exc)))
            return
        self.after(0, lambda: self._done(True, out_path.name))

    def _done(self, ok, msg):
        self.dl_btn.configure(state="normal")
        if ok:
            self.status_lbl.configure(text="✔ Téléchargé", bootstyle="success")
            self.app.set_status(f"Téléchargé : {msg}")
        else:
            self.status_lbl.configure(text="✘ Erreur", bootstyle="danger")
            messagebox.showerror("Erreur", f"Le téléchargement a échoué :\n{msg}")


class OsuDownloaderApp(tb.Window):
    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("osu! Beatmap Downloader")
        self.geometry("980x680")
        self.minsize(760, 480)

        self.download_dir = DEFAULT_DOWNLOAD_DIR
        self.results = []
        self.cards = []

        self._build_topbar()
        self._build_filters()
        self._build_results_area()
        self._build_bottombar()

    # ---------- construction UI ----------

    def _build_topbar(self):
        bar = tb.Frame(self, padding=10)
        bar.pack(fill="x")

        tb.Label(bar, text="osu! DOWNLOADER", font=("Segoe UI", 18, "bold"),
                  bootstyle="info").pack(side="left")

        theme_frame = tb.Frame(bar)
        theme_frame.pack(side="right")
        tb.Label(theme_frame, text="Thème :", bootstyle="secondary").pack(side="left", padx=(0, 4))
        self.theme_var = tb.StringVar(value="cyborg")
        theme_combo = tb.Combobox(theme_frame, textvariable=self.theme_var, values=THEMES,
                                   width=12, state="readonly", bootstyle="info")
        theme_combo.pack(side="left")
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self.change_theme())

    def _build_filters(self):
        filt = tb.Frame(self, padding=(10, 0, 10, 10))
        filt.pack(fill="x")

        self.search_var = tb.StringVar()
        entry = tb.Entry(filt, textvariable=self.search_var, bootstyle="info")
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        entry.bind("<Return>", lambda e: self.start_search())
        entry.focus()

        tb.Label(filt, text="Mode").pack(side="left", padx=(10, 2))
        self.mode_var = tb.StringVar(value="Tous")
        tb.Combobox(filt, textvariable=self.mode_var, values=list(MODES), width=8,
                    state="readonly", bootstyle="info").pack(side="left")

        tb.Label(filt, text="Statut").pack(side="left", padx=(10, 2))
        self.status_var = tb.StringVar(value="Tous")
        tb.Combobox(filt, textvariable=self.status_var, values=list(STATUSES), width=10,
                    state="readonly", bootstyle="info").pack(side="left")

        tb.Label(filt, text="★ min").pack(side="left", padx=(10, 2))
        self.minstar_var = tb.DoubleVar(value=0)
        tb.Spinbox(filt, from_=0, to=10, increment=0.5, textvariable=self.minstar_var,
                   width=5, bootstyle="info").pack(side="left")

        tb.Label(filt, text="Tri").pack(side="left", padx=(10, 2))
        self.sort_var = tb.StringVar(value="Pertinence")
        tb.Combobox(filt, textvariable=self.sort_var, values=list(SORTS), width=13,
                    state="readonly", bootstyle="info").pack(side="left")

        self.search_btn = tb.Button(filt, text="🔍 Rechercher", bootstyle="info",
                                     command=self.start_search)
        self.search_btn.pack(side="left", padx=(10, 0))

    def _build_results_area(self):
        outer = tb.Frame(self)
        outer.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        self.canvas = tb.Canvas(outer, highlightthickness=0)
        vscroll = tb.Scrollbar(outer, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.results_frame = tb.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.results_frame, anchor="nw", tags="frame")
        self.results_frame.bind("<Configure>",
                                 lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._resize_frame)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _resize_frame(self, event):
        self.canvas.itemconfig("frame", width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_bottombar(self):
        bar = tb.Frame(self, padding=10)
        bar.pack(fill="x")

        tb.Label(bar, text="Dossier :", bootstyle="secondary").pack(side="left")
        self.dir_var = tb.StringVar(value=str(self.download_dir))
        tb.Entry(bar, textvariable=self.dir_var, bootstyle="info").pack(
            side="left", fill="x", expand=True, padx=6)
        tb.Button(bar, text="Parcourir...", bootstyle="secondary-outline",
                  command=self.choose_dir).pack(side="left")
        tb.Button(bar, text="Ouvrir", bootstyle="secondary-outline",
                  command=self.open_dir).pack(side="left", padx=(6, 0))

        self.status_var_bottom = tb.StringVar(value="Prêt.")
        tb.Label(self, textvariable=self.status_var_bottom, bootstyle="secondary",
                  anchor="w", padding=(12, 0, 0, 8)).pack(fill="x")

    # ---------- actions ----------

    def change_theme(self):
        self.style.theme_use(self.theme_var.get())

    def set_status(self, text):
        self.status_var_bottom.set(text)

    def choose_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.home()))
        if chosen:
            self.dir_var.set(chosen)

    def open_dir(self):
        d = Path(self.dir_var.get())
        d.mkdir(parents=True, exist_ok=True)
        os.startfile(d)  # Windows uniquement

    def start_search(self):
        query = self.search_var.get().strip()
        if not query:
            return
        self.search_btn.configure(state="disabled")
        self.set_status(f"Recherche de « {query} »...")
        for c in self.cards:
            c.destroy()
        self.cards = []
        self.results = []
        threading.Thread(target=self._search_worker, args=(query,), daemon=True).start()

    def _search_worker(self, query):
        params = {"q": query, "ps": 40}
        mode = MODES.get(self.mode_var.get())
        status = STATUSES.get(self.status_var.get())
        sort = SORTS.get(self.sort_var.get())
        if mode is not None:
            params["m"] = mode
        if status is not None:
            params["s"] = status
        if sort:
            params["sort"] = sort
        try:
            resp = requests.get(API_SEARCH, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self.after(0, lambda: self._search_failed(exc))
            return
        min_star = self.minstar_var.get()
        if min_star:
            filtered = []
            for item in data:
                diffs = [b.get("difficulty_rating", 0) for b in item.get("beatmaps", [])]
                if diffs and max(diffs) >= min_star:
                    filtered.append(item)
            data = filtered
        self.after(0, lambda: self._search_done(data))

    def _search_failed(self, exc):
        self.search_btn.configure(state="normal")
        self.set_status("Échec de la recherche.")
        messagebox.showerror("Erreur", f"Impossible de contacter le miroir :\n{exc}")

    def _search_done(self, data):
        self.search_btn.configure(state="normal")
        self.results = data
        if not data:
            self.set_status("Aucun résultat.")
            return
        for i, item in enumerate(data):
            card = BeatmapCard(self.results_frame, self, item)
            card.grid(row=i // CARDS_PER_ROW, column=i % CARDS_PER_ROW,
                      sticky="nsew", padx=6, pady=6)
            self.cards.append(card)
        for col in range(CARDS_PER_ROW):
            self.results_frame.columnconfigure(col, weight=1)
        self.set_status(f"{len(data)} résultat(s).")


if __name__ == "__main__":
    app = OsuDownloaderApp()
    app.mainloop()