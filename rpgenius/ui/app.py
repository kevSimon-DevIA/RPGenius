"""Interface Tkinter principale."""

from __future__ import annotations

import io
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.request import urlopen

import sv_ttk
from PIL import Image, ImageDraw, ImageTk

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
WINDOW_VERTICAL_MARGIN = 80
HEADER_HEIGHT_RATIO = 0.08
SEARCH_DEBOUNCE_MS = 300


class MainWindow:
    """Fenêtre principale de l'application."""

    def __init__(self, service: SpotifyService, state: AppState | None = None) -> None:
        self._service = service
        self._state = state or AppState()

        self.root = tk.Tk()
        self.root.title("RPGenius – Ambiance Spotify")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self._target_width = max(screen_width // 2, 820)
        self._target_height = max(screen_height - WINDOW_VERTICAL_MARGIN, 540)

        self.root.geometry(f"{self._target_width}x{self._target_height}+0+0")
        self.root.minsize(self._target_width, self._target_height)
        self.root.resizable(True, False)

        sv_ttk.set_theme("dark")
        self.root.configure(bg=BACKGROUND_COLOR)
        self._configure_styles()

        self._device_var = tk.StringVar()
        self._search_var = tk.StringVar()
        self._search_after_id: str | None = None
        self._device_status_var = tk.StringVar(value="Aucun appareil sélectionné")
        self._profile_photo: ImageTk.PhotoImage | None = None
        self._profile_menu: tk.Menu | None = None
        self._profile_label: ttk.Label | None = None
        self._device_icon: ttk.Label | None = None
        self._device_menu: tk.Menu | None = None

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_main_area()
        self._update_auth_ui()

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
            "Speaker.TLabel",
            background=CARD_COLOR,
            font=("Helvetica", 18),
        )
        style.configure(
            "DeviceStatus.TLabel",
            background=CARD_COLOR,
            foreground=STATUS_NEUTRAL_COLOR,
            font=("Helvetica", 11),
        )
        style.configure(
            "Vertical.TScrollbar",
            troughcolor=CARD_COLOR,
            background=CARD_COLOR,
            bordercolor=CARD_COLOR,
        )
        style.configure(
            "Profile.TLabel",
            background=BACKGROUND_COLOR,
            foreground="#FFFFFF",
            padding=4,
        )
        self.root.option_add("*Font", "Helvetica 11")

    def _build_header(self) -> None:
        header_height = max(int(self._target_height * HEADER_HEIGHT_RATIO), 96)
        frame = ttk.Frame(self.root, style="Header.TFrame", padding=(24, 8))
        frame.grid(row=0, column=0, sticky="nwe")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=2)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.configure(height=header_height)
        frame.grid_propagate(False)

        self._status_label = ttk.Label(
            frame,
            text="Non connecté",
            style="Status.TLabel",
        )
        self._status_label.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self._search_entry = ttk.Entry(
            frame,
            textvariable=self._search_var,
            state="disabled",
            justify="center",
            width=48,
        )
        self._search_entry.grid(row=0, column=1, sticky="ew", padx=24, ipady=6)
        self._search_entry.bind("<Return>", lambda _: self.search_tracks(manual_trigger=True))
        self._search_var.trace_add("write", self._on_search_var_changed)

        self._profile_label = ttk.Label(
            frame,
            text="🙂",
            style="Profile.TLabel",
            cursor="hand2",
        )
        self._profile_label.grid(row=0, column=2, sticky="e", padx=(12, 0))
        self._profile_label.bind("<Button-1>", self._show_profile_menu)

        self._profile_menu = tk.Menu(self.root, tearoff=0)
        self._profile_menu.add_command(label="Déconnexion", command=self.disconnect_spotify)

    def _build_main_area(self) -> None:
        main_frame = ttk.Frame(self.root, padding=(24, 16, 24, 16), style="Main.TFrame")
        main_frame.grid(row=1, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self._auth_button = ttk.Button(
            main_frame,
            text="Connexion",
            command=self.authenticate_spotify,
            style="Accent.TButton",
        )
        self._auth_button.grid(row=0, column=0, sticky="w", pady=(0, 20))

        content_frame = ttk.Frame(main_frame, style="Main.TFrame")
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(1, weight=1)

        self._build_device_section(content_frame)
        self._build_results_section(content_frame)
        self._build_play_section(main_frame)

    def _build_device_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        label = ttk.Label(
            frame,
            text="Choisir un appareil de lecture Spotify",
            style="Section.TLabel",
        )
        label.grid(row=0, column=0, columnspan=2, sticky="w")

        self._device_icon = ttk.Label(
            frame,
            text="🔊",
            style="Speaker.TLabel",
            cursor="hand2",
        )
        self._device_icon.grid(row=1, column=0, sticky="w", pady=(14, 0))
        self._device_icon.bind("<Button-1>", self._open_device_menu)

        self._device_status_label = ttk.Label(
            frame,
            textvariable=self._device_status_var,
            style="DeviceStatus.TLabel",
        )
        self._device_status_label.grid(row=1, column=1, sticky="w", pady=(14, 0))

        self._device_menu = tk.Menu(self.root, tearoff=0)

        self._refresh_devices_button = ttk.Button(
            frame,
            text="Actualiser",
            command=self.refresh_devices,
            state=tk.DISABLED,
        )
        self._refresh_devices_button.grid(row=2, column=1, sticky="e", pady=(14, 0))

        self._update_device_icon()

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
        frame.grid(row=2, column=0, sticky="ew", pady=(24, 0))

        self._play_button = ttk.Button(
            frame,
            text="Jouer la piste sélectionnée",
            command=self.play_selected_track,
            style="Accent.TButton",
            state=tk.DISABLED,
        )
        self._play_button.pack(side=tk.RIGHT)

    def _on_search_var_changed(self, *_: object) -> None:
        if not self._state.is_authenticated:
            return
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(SEARCH_DEBOUNCE_MS, self.search_tracks)

    def _show_profile_menu(self, event: tk.Event) -> None:
        if not self._state.is_authenticated or not self._profile_menu:
            return

        try:
            self._profile_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._profile_menu.grab_release()

    def _update_profile_avatar(self) -> None:
        if not self._profile_label:
            return

        avatar_url = self._state.avatar_url if self._state.is_authenticated else None
        if not avatar_url:
            self._profile_label.configure(image="", text="🙂")
            self._profile_label.image = None
            return

        try:
            with urlopen(avatar_url, timeout=5) as response:
                buffer = io.BytesIO(response.read())
        except Exception:
            self._profile_label.configure(image="", text="🙂")
            self._profile_label.image = None
            return

        try:
            image = Image.open(buffer).convert("RGBA")
            image = image.resize((56, 56), Image.LANCZOS)
            mask = Image.new("L", image.size, 0)
            drawer = ImageDraw.Draw(mask)
            drawer.ellipse((0, 0, image.size[0], image.size[1]), fill=255)
            image.putalpha(mask)
            self._profile_photo = ImageTk.PhotoImage(image)
        except Exception:
            self._profile_photo = None

        if self._profile_photo:
            self._profile_label.configure(image=self._profile_photo, text="")
            self._profile_label.image = self._profile_photo
        else:
            self._profile_label.configure(image="", text="🙂")
            self._profile_label.image = None

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
        images = user.get("images") or []
        self._state.avatar_url = images[0].get("url") if images else None
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
            self._search_entry.focus()
            self._play_button.configure(state=tk.NORMAL)
            self._refresh_devices_button.configure(state=tk.NORMAL)
            self._update_device_icon()
        else:
            self._status_label.configure(text="Non connecté", foreground=STATUS_NEUTRAL_COLOR)
            self._auth_button.configure(
                text="Connexion",
                command=self.authenticate_spotify,
                state=tk.NORMAL,
            )
            if self._search_after_id:
                try:
                    self.root.after_cancel(self._search_after_id)
                except ValueError:
                    pass
                self._search_after_id = None
            self._search_entry.configure(state=tk.DISABLED)
            self._search_entry.delete(0, tk.END)
            self._search_var.set("")
            self._play_button.configure(state=tk.DISABLED)
            self._refresh_devices_button.configure(state=tk.DISABLED)
            self._results_listbox.delete(0, tk.END)
            self._state.clear_tracks()
            self._device_var.set("")
            if self._device_menu:
                self._device_menu.delete(0, "end")
            self._update_device_icon()
        self._update_profile_avatar()

    def search_tracks(self, manual_trigger: bool = False) -> None:
        if manual_trigger and self._search_after_id:
            try:
                self.root.after_cancel(self._search_after_id)
            except ValueError:
                pass
        self._search_after_id = None

        query = self._search_entry.get()

        if not query.strip():
            if manual_trigger:
                messagebox.showwarning(
                    "Recherche vide",
                    "Veuillez saisir un titre, un artiste ou un album.",
                )
            else:
                self._results_listbox.delete(0, tk.END)
                self._state.clear_tracks()
            return

        if not self._service.is_authenticated:
            if manual_trigger:
                messagebox.showerror(
                    "Non connecté",
                    "Connectez-vous à Spotify avant de lancer une recherche.",
                )
            return

        try:
            tracks = self._service.search_tracks(query, limit=20)
        except SpotifyServiceError as exc:
            if manual_trigger:
                messagebox.showerror(
                    "Erreur de recherche",
                    f"Impossible de contacter Spotify : {exc}",
                )
            return

        self._results_listbox.delete(0, tk.END)
        self._state.clear_tracks()

        if not tracks:
            if manual_trigger:
                messagebox.showinfo(
                    "Aucun résultat",
                    "Aucune piste trouvée pour cette recherche.",
                )
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
            self._device_var.set("")
            messagebox.showinfo(
                "Aucun appareil",
                "Ouvrez Spotify sur l'appareil désiré puis cliquez sur « Actualiser ».",
            )
            self._update_device_icon()
            return

        if previous_selection in self._state.device_map:
            self._device_var.set(previous_selection)
        else:
            self._device_var.set(device_names[0])

        self._update_device_icon()

    def _open_device_menu(self, event: tk.Event) -> None:
        """Affiche un menu avec les appareils disponibles."""
        if not self._service.is_authenticated or not self._device_menu:
            return

        device_names = list(self._state.device_map.keys())
        if not device_names:
            self.refresh_devices()
            return

        self._device_menu.delete(0, "end")
        for name in device_names:
            self._device_menu.add_command(
                label=name,
                command=lambda n=name: self._set_device(n),
            )

        try:
            self._device_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._device_menu.grab_release()

    def _set_device(self, device_name: str) -> None:
        """Mémorise l'appareil sélectionné et met à jour l'icône."""
        self._device_var.set(device_name)
        self._update_device_icon()

    def _update_device_icon(self) -> None:
        """Ajoute un retour visuel sur l'état de la sélection d'appareil."""
        if not self._device_icon:
            return

        selected_device = self._device_var.get()
        if selected_device:
            foreground = STATUS_SUCCESS_COLOR
            self._device_status_var.set(f"Appareil actif : {selected_device}")
        else:
            foreground = STATUS_ERROR_COLOR
            self._device_status_var.set("Aucun appareil sélectionné")

        self._device_icon.configure(foreground=foreground)

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

