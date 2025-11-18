"""Interface Tkinter principale."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from rpgenius.config import ConfigError
from rpgenius.services import SpotifyService, SpotifyServiceError
from rpgenius.state import AppState


class MainWindow:
    """Fenêtre principale de l'application."""

    def __init__(self, service: SpotifyService, state: AppState | None = None) -> None:
        self._service = service
        self._state = state or AppState()

        self.root = tk.Tk()
        self.root.title("RPGenius – Ambiance Spotify")
        self.root.geometry("520x420")

        self._device_var = tk.StringVar()
        self._build_ui()

    # --------------------------------------------------------------------- UI -
    def _build_ui(self) -> None:
        main_frame = tk.Frame(self.root, padx=12, pady=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._build_auth_section(main_frame)
        self._build_search_section(main_frame)
        self._build_device_section(main_frame)
        self._build_results_section(main_frame)
        self._build_play_section(main_frame)

    def _build_auth_section(self, parent: tk.Misc) -> None:
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))

        self._auth_button = tk.Button(
            frame,
            text="Se connecter à Spotify",
            command=self.authenticate_spotify,
            width=22,
        )
        self._auth_button.pack(side=tk.LEFT)

        self._status_label = tk.Label(frame, text="Non connecté", fg="red", padx=12)
        self._status_label.pack(side=tk.LEFT)

    def _build_search_section(self, parent: tk.Misc) -> None:
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))

        label = tk.Label(frame, text="Recherche :")
        label.pack(side=tk.LEFT)

        self._search_entry = tk.Entry(frame, width=40, state=tk.DISABLED)
        self._search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self._search_button = tk.Button(
            frame,
            text="Chercher",
            command=self.search_tracks,
            state=tk.DISABLED,
        )
        self._search_button.pack(side=tk.LEFT)

    def _build_device_section(self, parent: tk.Misc) -> None:
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))

        label = tk.Label(frame, text="Appareil :")
        label.pack(side=tk.LEFT)

        self._device_combo = ttk.Combobox(
            frame,
            textvariable=self._device_var,
            state="readonly",
            width=32,
        )
        self._device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self._refresh_devices_button = tk.Button(
            frame,
            text="Actualiser",
            command=self.refresh_devices,
            state=tk.DISABLED,
        )
        self._refresh_devices_button.pack(side=tk.LEFT)

    def _build_results_section(self, parent: tk.Misc) -> None:
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)

        self._results_listbox = tk.Listbox(frame, activestyle=tk.NONE)
        self._results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
        scrollbar.config(command=self._results_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._results_listbox.config(yscrollcommand=scrollbar.set)

    def _build_play_section(self, parent: tk.Misc) -> None:
        self._play_button = tk.Button(
            parent,
            text="Jouer la piste sélectionnée",
            command=self.play_selected_track,
            state=tk.DISABLED,
        )
        self._play_button.pack(pady=12)

    # --------------------------------------------------------------- Callbacks -
    def authenticate_spotify(self) -> None:
        try:
            user = self._service.authenticate()
        except ConfigError as exc:
            messagebox.showwarning("Identifiants manquants", str(exc))
            self._status_label.config(text="Identifiants absents", fg="red")
            return
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur d'authentification",
                f"Impossible de se connecter à Spotify : {exc}",
            )
            self._status_label.config(text="Échec de la connexion", fg="red")
            return

        self._state.username = user.get("display_name") or user.get("id")
        username = self._state.username or "Utilisateur"

        self._status_label.config(text=f"Connecté en tant que : {username}", fg="green")
        self._search_entry.config(state=tk.NORMAL)
        self._search_button.config(state=tk.NORMAL)
        self._play_button.config(state=tk.NORMAL)
        self._auth_button.config(state=tk.DISABLED)
        self._refresh_devices_button.config(state=tk.NORMAL)

        self.refresh_devices()

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

