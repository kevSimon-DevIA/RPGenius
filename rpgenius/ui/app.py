"""Interface Tkinter principale."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import sv_ttk

from rpgenius.config import ConfigError
from rpgenius.services import SpotifyService, SpotifyServiceError
from rpgenius.state import AppState

ACCENT_COLOR = "#1DB954"
BACKGROUND_COLOR = "#121212"
CARD_COLOR = "#181818"
STATUS_NEUTRAL_COLOR = "#B3B3B3"
STATUS_ERROR_COLOR = "#F87171"
STATUS_SUCCESS_COLOR = "#1DB954"
LISTBOX_SELECTION_FG = "#000000"


class MainWindow:
    """Fenêtre principale de l'application."""

    def __init__(self, service: SpotifyService, state: AppState | None = None) -> None:
        self._service = service
        self._state = state or AppState()

        self.root = tk.Tk()
        self.root.title("RPGenius – Ambiance Spotify")
        self.root.geometry("900x600")
        self.root.minsize(820, 540)

        sv_ttk.set_theme("dark")
        self.root.configure(bg=BACKGROUND_COLOR)
        self._configure_styles()

        self._device_var = tk.StringVar()
        self._search_var = tk.StringVar()
        self._build_ui()

    # --------------------------------------------------------------------- UI -
    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("Main.TFrame", background=BACKGROUND_COLOR)
        style.configure("Header.TFrame", background=BACKGROUND_COLOR)
        style.configure("Card.TFrame", background=CARD_COLOR)
        style.configure(
            "HeaderTitle.TLabel",
            background=BACKGROUND_COLOR,
            foreground="#FFFFFF",
            font=("Helvetica", 20, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=BACKGROUND_COLOR,
            foreground=STATUS_NEUTRAL_COLOR,
            font=("Helvetica", 11),
        )
        style.configure(
            "Section.TLabel",
            background=CARD_COLOR,
            foreground="#FFFFFF",
            font=("Helvetica", 12, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background=BACKGROUND_COLOR,
            foreground=STATUS_NEUTRAL_COLOR,
            font=("Helvetica", 11),
        )
        style.configure("Accent.TButton", font=("Helvetica", 11, "bold"))
        style.map(
            "Accent.TButton",
            background=[("active", "#1ED760"), ("pressed", "#1AA34A")],
        )
        style.configure("TButton", padding=(16, 8))
        style.map("TButton", background=[("disabled", "#2B2B2B")])
        style.configure(
            "Device.TCombobox",
            fieldbackground=CARD_COLOR,
            background=CARD_COLOR,
            foreground="#FFFFFF",
        )
        style.map(
            "Device.TCombobox",
            fieldbackground=[("readonly", CARD_COLOR)],
            foreground=[("readonly", "#FFFFFF")],
        )
        style.configure(
            "Vertical.TScrollbar",
            troughcolor=CARD_COLOR,
            background=CARD_COLOR,
            bordercolor=CARD_COLOR,
        )
        self.root.option_add("*Font", "Helvetica 11")

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding=(24, 24, 24, 16), style="Main.TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        self._build_auth_section(main_frame)
        self._build_search_section(main_frame)

        content_frame = ttk.Frame(main_frame, style="Main.TFrame")
        content_frame.grid(row=2, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)

        self._build_device_section(content_frame)
        self._build_results_section(content_frame)
        self._build_play_section(main_frame)
        self._update_auth_ui()

    def _build_auth_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Header.TFrame")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        frame.columnconfigure(0, weight=1)

        title = ttk.Label(frame, text="RPGenius", style="HeaderTitle.TLabel")
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            frame,
            text="Trouvez la bonne ambiance Spotify en un clin d'oeil",
            style="Subtitle.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self._auth_button = ttk.Button(
            frame,
            text="Connexion",
            command=self.authenticate_spotify,
            style="Accent.TButton",
        )
        self._auth_button.grid(row=0, column=1, rowspan=2, sticky="e")

        self._status_label = ttk.Label(
            frame,
            text="Non connecté",
            style="Status.TLabel",
        )
        self._status_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _build_search_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        frame.columnconfigure(0, weight=1)

        label = ttk.Label(
            frame,
            text="Rechercher un titre, un artiste ou une ambiance",
            style="Section.TLabel",
        )
        label.grid(row=0, column=0, columnspan=2, sticky="w")

        self._search_entry = ttk.Entry(
            frame,
            textvariable=self._search_var,
            state="disabled",
        )
        self._search_entry.grid(row=1, column=0, sticky="ew", pady=(14, 0), padx=(0, 12))

        self._search_button = ttk.Button(
            frame,
            text="Chercher",
            command=self.search_tracks,
            style="Accent.TButton",
            state=tk.DISABLED,
        )
        self._search_button.grid(row=1, column=1, sticky="ew", pady=(14, 0))

    def _build_device_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)

        label = ttk.Label(
            frame,
            text="Choisir un appareil de lecture Spotify",
            style="Section.TLabel",
        )
        label.grid(row=0, column=0, columnspan=2, sticky="w")

        self._device_combo = ttk.Combobox(
            frame,
            textvariable=self._device_var,
            state="readonly",
            style="Device.TCombobox",
        )
        self._device_combo.grid(row=1, column=0, sticky="ew", pady=(14, 0), padx=(0, 12))

        self._refresh_devices_button = ttk.Button(
            frame,
            text="Actualiser",
            command=self.refresh_devices,
            state=tk.DISABLED,
        )
        self._refresh_devices_button.grid(row=1, column=1, sticky="ew", pady=(14, 0))

    def _build_results_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        frame.grid(row=1, column=0, sticky="nsew", pady=(20, 0))
        parent.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        label = ttk.Label(
            frame,
            text="Résultats de recherche",
            style="Section.TLabel",
        )
        label.grid(row=0, column=0, sticky="w")

        list_container = ttk.Frame(frame, style="Card.TFrame")
        list_container.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self._results_listbox = tk.Listbox(
            list_container,
            activestyle=tk.NONE,
            bg=CARD_COLOR,
            fg="#FFFFFF",
            font=("Helvetica", 11),
            highlightthickness=0,
            selectbackground=ACCENT_COLOR,
            selectforeground=LISTBOX_SELECTION_FG,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self._results_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            list_container,
            orient=tk.VERTICAL,
            command=self._results_listbox.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._results_listbox.configure(yscrollcommand=scrollbar.set)

    def _build_play_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Main.TFrame")
        frame.grid(row=3, column=0, sticky="ew", pady=(24, 0))

        self._play_button = ttk.Button(
            frame,
            text="Jouer la piste sélectionnée",
            command=self.play_selected_track,
            style="Accent.TButton",
            state=tk.DISABLED,
        )
        self._play_button.pack(side=tk.RIGHT)

    # --------------------------------------------------------------- Callbacks -
    def authenticate_spotify(self) -> None:
        try:
            user = self._service.authenticate()
        except ConfigError as exc:
            messagebox.showwarning("Identifiants manquants", str(exc))
            self._status_label.configure(
                text="Identifiants absents",
                foreground=STATUS_ERROR_COLOR,
            )
            return
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur d'authentification",
                f"Impossible de se connecter à Spotify : {exc}",
            )
            self._status_label.configure(
                text="Échec de la connexion",
                foreground=STATUS_ERROR_COLOR,
            )
            return

        self._state.username = user.get("display_name") or user.get("id")
        self._update_auth_ui()

        self.refresh_devices()

    def disconnect_spotify(self) -> None:
        """Déconnecte l'utilisateur de Spotify."""
        if not self._service.is_authenticated:
            return

        self._service.logout()
        self._state.reset()
        self._update_auth_ui()

    def _update_auth_ui(self) -> None:
        """Met à jour l'interface en fonction de l'état d'authentification."""
        is_authenticated = self._state.is_authenticated

        if is_authenticated:
            username = self._state.username or "Utilisateur"
            self._status_label.configure(
                text=f"Connecté en tant que : {username}",
                foreground=STATUS_SUCCESS_COLOR,
            )
            self._auth_button.configure(
                text="Déconnexion",
                command=self.disconnect_spotify,
                state=tk.NORMAL,
            )
            self._search_entry.configure(state=tk.NORMAL)
            self._search_button.configure(state=tk.NORMAL)
            self._play_button.configure(state=tk.NORMAL)
            self._refresh_devices_button.configure(state=tk.NORMAL)
        else:
            self._status_label.configure(text="Non connecté", foreground=STATUS_NEUTRAL_COLOR)
            self._auth_button.configure(
                text="Connexion",
                command=self.authenticate_spotify,
                state=tk.NORMAL,
            )
            self._search_entry.configure(state=tk.DISABLED)
            self._search_entry.delete(0, tk.END)
            self._search_var.set("")
            self._search_button.configure(state=tk.DISABLED)
            self._play_button.configure(state=tk.DISABLED)
            self._refresh_devices_button.configure(state=tk.DISABLED)
            self._results_listbox.delete(0, tk.END)
            self._device_combo.set("")
            self._device_combo["values"] = []
            self._device_var.set("")

    def search_tracks(self) -> None:
        query = self._search_entry.get()

        if not query.strip():
            messagebox.showwarning(
                "Recherche vide",
                "Veuillez saisir un titre, un artiste ou un album.",
            )
            return

        if not self._service.is_authenticated:
            messagebox.showerror(
                "Non connecté",
                "Connectez-vous à Spotify avant de lancer une recherche.",
            )
            return

        try:
            tracks = self._service.search_tracks(query, limit=20)
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur de recherche",
                f"Impossible de contacter Spotify : {exc}",
            )
            return

        self._results_listbox.delete(0, tk.END)
        self._state.clear_tracks()

        if not tracks:
            messagebox.showinfo("Aucun résultat", "Aucune piste trouvée pour cette recherche.")
            return

        entries: list[tuple[str, str]] = []
        for track in tracks:
            title = track.get("name", "Sans titre")
            artist = track.get("artists", [{}])[0].get("name", "Artiste inconnu")
            display_name = f"{title} – {artist}"
            uri = track.get("uri", "")
            self._results_listbox.insert(tk.END, display_name)
            entries.append((display_name, uri))

        self._state.set_tracks(entries)

    def refresh_devices(self) -> None:
        if not self._service.is_authenticated:
            messagebox.showwarning(
                "Non connecté",
                "Connectez-vous à Spotify pour lister vos appareils.",
            )
            return

        try:
            devices = self._service.list_devices()
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur Spotify",
                f"Impossible de récupérer vos appareils Spotify : {exc}",
            )
            return

        self._state.set_devices(
            (device.get("name", "Appareil inconnu"), device.get("id", ""))
            for device in devices
        )

        device_names = list(self._state.device_map.keys())
        previous_selection = self._device_var.get()

        if not device_names:
            self._device_combo["values"] = []
            self._device_var.set("")
            messagebox.showinfo(
                "Aucun appareil",
                "Ouvrez Spotify sur l'appareil désiré puis cliquez sur « Actualiser ».",
            )
            return

        self._device_combo["values"] = device_names

        if previous_selection in self._state.device_map:
            self._device_var.set(previous_selection)
        else:
            self._device_var.set(device_names[0])

    def play_selected_track(self) -> None:
        if not self._service.is_authenticated:
            messagebox.showerror(
                "Non connecté",
                "Connectez-vous à Spotify avant de lancer la lecture.",
            )
            return

        selection = self._results_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "Aucune sélection",
                "Veuillez choisir une piste dans la liste.",
            )
            return

        display_name = self._results_listbox.get(selection[0])
        track_uri = self._state.track_uris.get(display_name)

        if not track_uri:
            messagebox.showerror(
                "URI introuvable",
                "Impossible de retrouver la piste sélectionnée.",
            )
            return

        selected_device_name = self._device_var.get()
        if not selected_device_name:
            messagebox.showwarning(
                "Aucun appareil sélectionné",
                "Choisissez un appareil dans la liste puis relancez la lecture.",
            )
            return

        device_id = self._state.get_device_id(selected_device_name)
        if not device_id:
            messagebox.showwarning(
                "Aucun appareil sélectionné",
                "Choisissez un appareil dans la liste puis relancez la lecture.",
            )
            return

        try:
            self._service.start_playback(device_id=device_id, uris=[track_uri])
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Lecture impossible",
                "Spotify n'a pas pu lancer la piste. Assurez-vous que la lecture "
                f"est bien possible sur l'appareil actif.\n\nDétails : {exc}",
            )

    # ----------------------------------------------------------------- Public -
    def run(self) -> None:
        self.root.mainloop()

