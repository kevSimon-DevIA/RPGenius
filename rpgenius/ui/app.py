"""Interface Tkinter principale."""

from __future__ import annotations

import io
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any
from urllib.request import urlopen

import sv_ttk
from PIL import Image, ImageDraw, ImageOps, ImageTk

from rpgenius.config import ConfigError
from rpgenius.services import SpotifyService, SpotifyServiceError
from rpgenius.state import AppState

ACCENT_COLOR = "#1DB954"
BACKGROUND_COLOR = "#F5F5F7"
CARD_COLOR = "#FFFFFF"
STATUS_NEUTRAL_COLOR = "#4B5563"
STATUS_ERROR_COLOR = "#DC2626"
STATUS_SUCCESS_COLOR = "#15803D"
LISTBOX_SELECTION_FG = "#000000"
WINDOW_VERTICAL_MARGIN = 80
HEADER_HEIGHT_RATIO = 0.06
SEARCH_DEBOUNCE_MS = 300
SEARCH_BG_COLOR = "#FFFFFF"
SEARCH_BORDER_COLOR = "#D1D5DB"
SEARCH_PLACEHOLDER = "Que souhaitez-vous écouter ou regarder ?"
SEARCH_PLACEHOLDER_COLOR = "#9CA3AF"
SEARCH_TEXT_COLOR = "#111827"
ASSETS_PATH = "rpgenius/assets"
AVATAR_IMAGE_SIZE = 72


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
        self.root.minsize(600, 400)
        self.root.resizable(True, True)
        
        # Bind resize event for responsive layout
        self.root.bind("<Configure>", self._on_window_resize)

        sv_ttk.set_theme("light")
        self.root.configure(bg=BACKGROUND_COLOR)
        self._configure_styles()

        self._device_var = tk.StringVar()
        self._search_var = tk.StringVar()
        self._search_after_id: str | None = None
        self._device_status_var = tk.StringVar(value="Aucun appareil sélectionné")
        self._profile_photo: ImageTk.PhotoImage | None = None
        self._profile_menu: tk.Menu | None = None
        self._profile_label: tk.Label | None = None
        self._avatar_container: tk.Frame | None = None
        self._current_avatar_size: int = AVATAR_IMAGE_SIZE
        self._search_entry: tk.Entry | None = None
        self._search_container: tk.Frame | None = None
        self._search_separator: tk.Frame | None = None
        self._search_action_icon: tk.Label | None = None
        self._search_placeholder_active = True
        self._suspend_search_callback = False
        self._device_icon: ttk.Label | None = None
        self._device_menu: tk.Menu | None = None

        self._results_canvas: tk.Canvas | None = None
        self._results_scrollable_frame: tk.Frame | None = None
        self._results_canvas_window: int | None = None  # ID de la fenêtre du canvas
        self._result_items: list[tuple[str, tk.Frame]] = []  # Liste des éléments de résultat (display_name, frame)
        self._result_images: dict[str, ImageTk.PhotoImage] = {}  # Cache des images redimensionnées

        self._player_frame: ttk.Frame | None = None
        self._play_pause_button: ttk.Button | None = None
        self._previous_button: ttk.Button | None = None
        self._next_button: ttk.Button | None = None
        self._progress_bar: ttk.Progressbar | None = None
        self._time_label: tk.Label | None = None
        self._remaining_time_label: tk.Label | None = None
        self._progress_update_job: str | None = None
        self._is_playing = False
        
        # Éléments d'affichage du titre actuel
        self._current_track_image: ImageTk.PhotoImage | None = None
        self._current_track_image_label: tk.Label | None = None
        self._current_track_title_label: tk.Label | None = None
        self._current_track_artist_label: tk.Label | None = None
        self._current_track_frame: ttk.Frame | None = None

        self._icon_search: ImageTk.PhotoImage | None = None
        self._icon_folder: ImageTk.PhotoImage | None = None
        self._icon_speaker_on: ImageTk.PhotoImage | None = None
        self._icon_speaker_off: ImageTk.PhotoImage | None = None
        self._icon_play: ImageTk.PhotoImage | None = None
        self._icon_pause: ImageTk.PhotoImage | None = None
        self._icon_next: ImageTk.PhotoImage | None = None
        self._icon_previous: ImageTk.PhotoImage | None = None
        
        self._header_frame: ttk.Frame | None = None
        self._search_frame: ttk.Frame | None = None
        self._device_frame: ttk.Frame | None = None
        self._results_frame: ttk.Frame | None = None

        self._load_icons()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        self._build_header()
        self._build_main_area()
        self._update_player_icons()
        self._update_auth_ui()
        
        # Tenter une authentification automatique depuis le cache
        self._try_auto_authenticate()
        
        # Appliquer le layout responsive initial après que la fenêtre soit affichée
        self.root.after(100, self._apply_responsive_layout)

    # --------------------------------------------------------------------- UI -
    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("Main.TFrame", background=BACKGROUND_COLOR)
        style.configure("Header.TFrame", background=BACKGROUND_COLOR)
        style.configure("Card.TFrame", background=CARD_COLOR)
        style.configure(
            "HeaderTitle.TLabel",
            background=BACKGROUND_COLOR,
            foreground="#0F172A",
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
            foreground="#0F172A",
            font=("Helvetica", 12, "bold"),
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
            background="#E5E7EB",
            bordercolor="#E5E7EB",
        )
        self.root.option_add("*Font", "Helvetica 11")

    def _build_header(self) -> None:
        frame = ttk.Frame(self.root, style="Header.TFrame", padding=(24, 8))
        frame.grid(row=0, column=0, sticky="nwe")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(0, weight=1)
        self._header_frame = frame

        ttk.Frame(frame, style="Header.TFrame").grid(row=0, column=0, sticky="nsew")

        search_frame = ttk.Frame(frame, style="Header.TFrame")
        search_frame.grid(row=0, column=1, sticky="nsew", padx=24)
        search_frame.rowconfigure(0, weight=1)
        search_frame.columnconfigure(0, weight=1)
        self._search_frame = search_frame

        self._search_container = tk.Frame(
            search_frame,
            bg=SEARCH_BG_COLOR,
            bd=0,
            highlightthickness=1,
            highlightbackground=SEARCH_BORDER_COLOR,
            highlightcolor=SEARCH_BORDER_COLOR,
        )
        self._search_container.grid(row=0, column=0, sticky="nsew", pady=6)

        search_icon = tk.Label(
            self._search_container,
            bg=SEARCH_BG_COLOR,
        )
        if self._icon_search:
            search_icon.configure(image=self._icon_search)
        search_icon.pack(side=tk.LEFT, padx=(18, 12))

        self._search_entry = tk.Entry(
            self._search_container,
            textvariable=self._search_var,
            bg=SEARCH_BG_COLOR,
            fg=SEARCH_TEXT_COLOR,
            insertbackground=SEARCH_TEXT_COLOR,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
        )
        self._search_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._search_entry.configure(font=("Helvetica", 12))
        self._search_entry.configure(disabledbackground=SEARCH_BG_COLOR, disabledforeground=SEARCH_PLACEHOLDER_COLOR)
        self._search_entry.bind("<Return>", lambda _: self.search_tracks(manual_trigger=True))
        self._search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self._search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self._search_var.trace_add("write", self._on_search_var_changed)

        self._search_separator = tk.Frame(
            self._search_container,
            bg=SEARCH_BORDER_COLOR,
            width=1,
        )
        self._search_separator.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 12), pady=10)

        self._search_action_icon = tk.Label(
            self._search_container,
            bg=SEARCH_BG_COLOR,
        )
        if self._icon_folder:
            self._search_action_icon.configure(image=self._icon_folder)
        self._search_action_icon.pack(side=tk.LEFT, padx=(0, 18))

        self._avatar_container = tk.Frame(
            frame,
            bg=BACKGROUND_COLOR,
            width=AVATAR_IMAGE_SIZE,
            height=AVATAR_IMAGE_SIZE,
        )
        self._avatar_container.grid(row=0, column=2, sticky="e", padx=(12, 0))
        self._avatar_container.grid_propagate(False)

        self._profile_label = tk.Label(
            self._avatar_container,
            text="🙂",
            bg=BACKGROUND_COLOR,
            cursor="hand2",
            bd=0,
            highlightthickness=0,
        )
        self._profile_label.place(relx=0.5, rely=0.5, anchor="center")
        self._profile_label.bind("<Button-1>", self._show_profile_menu)

        self._profile_menu = tk.Menu(self.root, tearoff=0)
        self._profile_menu.add_command(label="Déconnexion", command=self.disconnect_spotify)

        self._set_search_placeholder()

    def _build_main_area(self) -> None:
        main_frame = ttk.Frame(self.root, padding=(24, 16, 24, 16), style="Main.TFrame")
        main_frame.grid(row=1, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self._main_frame = main_frame

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
        
        self._build_player_controls()

    def _build_device_section(self, parent: tk.Misc) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=(20, 18))
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        self._device_frame = frame

        label = ttk.Label(
            frame,
            text="Choisir un appareil de lecture Spotify",
            style="Section.TLabel",
        )
        label.grid(row=0, column=0, columnspan=2, sticky="w")

        self._device_icon = ttk.Label(
            frame,
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
        self._results_frame = frame

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

        # Canvas avec scrollbar pour afficher les résultats avec images
        self._results_canvas = tk.Canvas(
            list_container,
            bg="#F8FAFC",
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self._results_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            list_container,
            orient=tk.VERTICAL,
            command=self._results_canvas.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._results_canvas.configure(yscrollcommand=scrollbar.set)

        # Frame scrollable à l'intérieur du canvas
        self._results_scrollable_frame = tk.Frame(
            self._results_canvas,
            bg="#F8FAFC",
        )
        self._results_canvas_window = self._results_canvas.create_window(
            (0, 0),
            window=self._results_scrollable_frame,
            anchor="nw",
        )

        # Configurer le scroll
        def configure_scroll_region(_: object) -> None:
            self._results_canvas.configure(scrollregion=self._results_canvas.bbox("all"))

        def configure_canvas_width(_: object) -> None:
            canvas_width = self._results_canvas.winfo_width()
            if canvas_width > 1:  # Éviter les valeurs invalides
                self._results_canvas.itemconfig(self._results_canvas_window, width=canvas_width)

        self._results_scrollable_frame.bind("<Configure>", configure_scroll_region)
        self._results_canvas.bind("<Configure>", configure_canvas_width)

        # Bind la molette de la souris pour le scroll
        def on_mousewheel(event: tk.Event) -> None:
            """Gère le scroll avec la molette de la souris."""
            if not self._results_canvas:
                return
            # Windows/Linux avec delta
            if hasattr(event, 'delta') and event.delta:
                self._results_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            # Linux avec numéro d'événement
            elif hasattr(event, 'num'):
                if event.num == 4:
                    self._results_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self._results_canvas.yview_scroll(1, "units")

        # Bind sur le canvas
        self._results_canvas.bind("<MouseWheel>", on_mousewheel)
        self._results_canvas.bind("<Button-4>", on_mousewheel)  # Linux scroll up
        self._results_canvas.bind("<Button-5>", on_mousewheel)  # Linux scroll down
        
        # Permettre au canvas de recevoir le focus pour le scroll au clavier
        self._results_canvas.configure(takefocus=True)
        
        # Bind les touches flèches pour le scroll au clavier
        def on_arrow_key(event: tk.Event) -> None:
            """Gère le scroll avec les touches du clavier."""
            if not self._results_canvas:
                return
            if event.keysym == "Up":
                self._results_canvas.yview_scroll(-1, "units")
            elif event.keysym == "Down":
                self._results_canvas.yview_scroll(1, "units")
            elif event.keysym == "Page_Up":
                self._results_canvas.yview_scroll(-1, "pages")
            elif event.keysym == "Page_Down":
                self._results_canvas.yview_scroll(1, "pages")
            elif event.keysym == "Home":
                self._results_canvas.yview_moveto(0)
            elif event.keysym == "End":
                self._results_canvas.yview_moveto(1)
        
        self._results_canvas.bind("<KeyPress>", on_arrow_key)
        
        # Bind également sur le frame scrollable pour capturer les événements de scroll
        def bind_mousewheel_to_frame(widget: tk.Widget) -> None:
            """Bind les événements de scroll sur un widget."""
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
        
        # Bind initial sur le frame scrollable
        bind_mousewheel_to_frame(self._results_scrollable_frame)

    def _build_player_controls(self) -> None:
        """Construit le conteneur de contrôle de lecture en bas de l'application."""
        frame = ttk.Frame(self.root, style="Header.TFrame", padding=(24, 8))
        frame.grid(row=2, column=0, sticky="nwe")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        self._player_frame = frame

        # Conteneur pour l'affichage du titre actuel
        track_info_frame = ttk.Frame(frame, style="Header.TFrame")
        track_info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        track_info_frame.columnconfigure(1, weight=1)
        self._current_track_frame = track_info_frame

        # Image du morceau actuel
        self._current_track_image_label = tk.Label(
            track_info_frame,
            bg=BACKGROUND_COLOR,
            width=60,
            height=60,
            text="♪",
            font=("Helvetica", 24),
            fg="#9CA3AF",
        )
        self._current_track_image_label.grid(row=0, column=0, padx=(0, 12), sticky="nw")

        # Conteneur pour le titre et l'artiste
        track_text_frame = ttk.Frame(track_info_frame, style="Header.TFrame")
        track_text_frame.grid(row=0, column=1, sticky="w")

        # Titre du morceau actuel
        self._current_track_title_label = tk.Label(
            track_text_frame,
            text="Aucune lecture en cours",
            bg=BACKGROUND_COLOR,
            fg="#0F172A",
            font=("Helvetica", 12, "bold"),
            anchor="w",
        )
        self._current_track_title_label.grid(row=0, column=0, sticky="w")

        # Artiste du morceau actuel
        self._current_track_artist_label = tk.Label(
            track_text_frame,
            text="",
            bg=BACKGROUND_COLOR,
            fg="#6B7280",
            font=("Helvetica", 11),
            anchor="w",
        )
        self._current_track_artist_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Conteneur pour les boutons de contrôle
        controls_frame = ttk.Frame(frame, style="Header.TFrame")
        controls_frame.grid(row=1, column=0, sticky="nsew")
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=0)
        controls_frame.columnconfigure(2, weight=0)
        controls_frame.columnconfigure(3, weight=0)
        controls_frame.columnconfigure(4, weight=1)

        # Espaceur gauche
        ttk.Frame(controls_frame, style="Header.TFrame").grid(row=0, column=0, sticky="nsew")

        # Bouton précédent
        self._previous_button = ttk.Button(
            controls_frame,
            image=self._icon_previous,
            command=self._previous_track,
            state=tk.DISABLED,
        )
        if self._icon_previous:
            self._previous_button.image = self._icon_previous
        self._previous_button.grid(row=0, column=1, padx=8)

        # Bouton lecture/pause
        self._play_pause_button = ttk.Button(
            controls_frame,
            image=self._icon_play,
            command=self._toggle_play_pause,
            state=tk.DISABLED,
        )
        if self._icon_play:
            self._play_pause_button.image = self._icon_play
        self._play_pause_button.grid(row=0, column=2, padx=8)

        # Bouton suivant
        self._next_button = ttk.Button(
            controls_frame,
            image=self._icon_next,
            command=self._next_track,
            state=tk.DISABLED,
        )
        if self._icon_next:
            self._next_button.image = self._icon_next
        self._next_button.grid(row=0, column=3, padx=8)

        # Espaceur droit
        ttk.Frame(controls_frame, style="Header.TFrame").grid(row=0, column=4, sticky="nsew")

        # Conteneur pour la barre de progression
        progress_frame = ttk.Frame(frame, style="Header.TFrame")
        progress_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        progress_frame.columnconfigure(1, weight=1)

        # Label du temps actuel
        self._time_label = tk.Label(
            progress_frame,
            text="0:00",
            bg=BACKGROUND_COLOR,
            fg="#0F172A",
            font=("Helvetica", 10),
        )
        self._time_label.grid(row=0, column=0, padx=(0, 12))

        # Barre de progression
        self._progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            length=200,
            style="TProgressbar",
        )
        self._progress_bar.grid(row=0, column=1, sticky="ew", padx=0)

        # Label du temps restant
        self._remaining_time_label = tk.Label(
            progress_frame,
            text="-0:00",
            bg=BACKGROUND_COLOR,
            fg="#0F172A",
            font=("Helvetica", 10),
        )
        self._remaining_time_label.grid(row=0, column=2, padx=(12, 0))

    def _update_player_icons(self) -> None:
        """Met à jour les icônes des boutons de contrôle après leur création."""
        if self._previous_button and self._icon_previous:
            self._previous_button.configure(image=self._icon_previous)
            self._previous_button.image = self._icon_previous
        elif self._previous_button:
            self._previous_button.configure(text="⏮")
        
        if self._next_button and self._icon_next:
            self._next_button.configure(image=self._icon_next)
            self._next_button.image = self._icon_next
        elif self._next_button:
            self._next_button.configure(text="⏭")
        
        if self._play_pause_button:
            if self._is_playing and self._icon_pause:
                self._play_pause_button.configure(image=self._icon_pause)
                self._play_pause_button.image = self._icon_pause
            elif not self._is_playing and self._icon_play:
                self._play_pause_button.configure(image=self._icon_play)
                self._play_pause_button.image = self._icon_play
            elif not self._icon_play and not self._icon_pause:
                self._play_pause_button.configure(text="▶" if not self._is_playing else "⏸")

    def _load_icons(self) -> None:
        try:
            icon_size = (20, 20)
            speaker_size = (24, 24)
            player_icon_size = (24, 24)

            search_img = Image.open(f"{ASSETS_PATH}/search.png").convert("RGBA")
            self._icon_search = ImageTk.PhotoImage(search_img.resize(icon_size, Image.LANCZOS))

            folder_img = Image.open(f"{ASSETS_PATH}/folder.png").convert("RGBA")
            self._icon_folder = ImageTk.PhotoImage(folder_img.resize(icon_size, Image.LANCZOS))

            speaker_on_img = Image.open(f"{ASSETS_PATH}/speaker_on.png").convert("RGBA")
            self._icon_speaker_on = ImageTk.PhotoImage(
                speaker_on_img.resize(speaker_size, Image.LANCZOS)
            )

            speaker_off_img = Image.open(f"{ASSETS_PATH}/speaker_off.png").convert("RGBA")
            self._icon_speaker_off = ImageTk.PhotoImage(
                speaker_off_img.resize(speaker_size, Image.LANCZOS)
            )

            play_img = Image.open(f"{ASSETS_PATH}/play.png").convert("RGBA")
            self._icon_play = ImageTk.PhotoImage(play_img.resize(player_icon_size, Image.LANCZOS))

            pause_img = Image.open(f"{ASSETS_PATH}/pause.png").convert("RGBA")
            self._icon_pause = ImageTk.PhotoImage(pause_img.resize(player_icon_size, Image.LANCZOS))

            next_img = Image.open(f"{ASSETS_PATH}/next.png").convert("RGBA")
            self._icon_next = ImageTk.PhotoImage(next_img.resize(player_icon_size, Image.LANCZOS))

            last_img = Image.open(f"{ASSETS_PATH}/last.png").convert("RGBA")
            self._icon_previous = ImageTk.PhotoImage(last_img.resize(player_icon_size, Image.LANCZOS))

        except FileNotFoundError:
            messagebox.showwarning(
                "Icônes manquantes",
                f"Certains fichiers d'icônes sont introuvables dans '{ASSETS_PATH}'. "
                "L'affichage peut être dégradé.",
            )
        except Exception as exc:
            messagebox.showerror("Erreur de chargement des icônes", str(exc))

    def _on_window_resize(self, event: tk.Event) -> None:
        """Gère le redimensionnement de la fenêtre pour adapter l'interface."""
        if event.widget != self.root:
            return
        
        # Attendre que la fenêtre soit complètement redimensionnée
        self.root.after_idle(self._apply_responsive_layout)
    
    def _apply_responsive_layout(self) -> None:
        """Applique les ajustements de layout responsive."""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Ignorer les appels trop tôt (fenêtre pas encore initialisée)
        if width < 100 or height < 100:
            return
        
        if width < 700:
            # Très petits écrans : padding minimal
            padding_x = 8
            padding_y = 4
            search_padx = 8
            card_padding_x = 10
            card_padding_y = 10
        elif width < 800:
            # Petits écrans : padding réduit
            padding_x = 12
            padding_y = 6
            search_padx = 12
            card_padding_x = 12
            card_padding_y = 12
        elif width < 1200:
            # Écrans moyens : padding modéré
            padding_x = 18
            padding_y = 8
            search_padx = 18
            card_padding_x = 16
            card_padding_y = 14
        else:
            # Grands écrans : padding normal
            padding_x = 24
            padding_y = 8
            search_padx = 24
            card_padding_x = 20
            card_padding_y = 18
        
        if self._header_frame:
            self._header_frame.configure(padding=(padding_x, padding_y))
        
        if self._player_frame:
            self._player_frame.configure(padding=(padding_x, padding_y))
        
        if self._main_frame:
            if width < 700:
                main_padding_x = 8
                main_padding_y = 6 if height >= 500 else 4
            elif width < 800:
                main_padding_x = 12
                main_padding_y = 8 if height >= 500 else 6
            else:
                main_padding_x = padding_x
                main_padding_y = 12 if height >= 600 else 8
            self._main_frame.configure(padding=(main_padding_x, main_padding_y, main_padding_x, main_padding_y))
        
        if self._search_frame:
            self._search_frame.grid_configure(padx=search_padx)
        
        # Ajuster la taille de l'avatar selon la taille de la fenêtre
        if self._avatar_container and self._header_frame:
            try:
                header_height = self._header_frame.winfo_height()
                if header_height > 0:
                    # Calculer la taille de l'avatar selon la largeur ET la hauteur
                    if width < 700:
                        # Très petits écrans : avatar plus petit
                        avatar_size = min(max(header_height - 20, 40), 56)
                    elif width < 800:
                        # Petits écrans : avatar moyen
                        avatar_size = min(max(header_height - 16, 48), 64)
                    else:
                        # Écrans normaux : avatar taille normale
                        avatar_size = min(max(header_height - 16, 48), AVATAR_IMAGE_SIZE)
                    
                    # Mettre à jour le conteneur seulement si la taille a changé
                    if avatar_size != self._current_avatar_size:
                        self._avatar_container.configure(width=avatar_size, height=avatar_size)
                        self._avatar_container.grid_propagate(False)
                        # Recharger l'image de l'avatar avec la nouvelle taille si l'utilisateur est connecté
                        if self._state.is_authenticated and self._state.avatar_url:
                            self._update_profile_avatar(avatar_size)
            except tk.TclError:
                pass  # Fenêtre pas encore complètement initialisée
        
        # Ajuster la taille de police selon la largeur
        if width < 700:
            search_font_size = 11
        elif width < 1000:
            search_font_size = 12
        else:
            search_font_size = 12
        
        if self._search_entry:
            self._search_entry.configure(font=("Helvetica", search_font_size))
        
        # Ajuster le padding des cartes
        if self._device_frame:
            self._device_frame.configure(padding=(card_padding_x, card_padding_y))
        if self._results_frame:
            self._results_frame.configure(padding=(card_padding_x, card_padding_y))

    def _set_search_placeholder(self) -> None:
        if not self._search_entry:
            return
        self._suspend_search_callback = True
        self._search_placeholder_active = True
        self._search_var.set(SEARCH_PLACEHOLDER)
        self._search_entry.configure(foreground=SEARCH_PLACEHOLDER_COLOR)
        self._suspend_search_callback = False

    def _clear_search_placeholder(self) -> None:
        if not self._search_entry:
            return
        if not self._search_placeholder_active:
            return
        self._suspend_search_callback = True
        self._search_placeholder_active = False
        self._search_var.set("")
        self._suspend_search_callback = False
        self._search_entry.configure(foreground=SEARCH_TEXT_COLOR)

    def _on_search_focus_in(self, _: tk.Event) -> None:
        if not self._search_entry or str(self._search_entry.cget("state")) == "disabled":
            return
        if self._search_placeholder_active:
            self._clear_search_placeholder()

    def _on_search_focus_out(self, _: tk.Event) -> None:
        if not self._search_entry or str(self._search_entry.cget("state")) == "disabled":
            return
        if not self._search_var.get().strip():
            self._set_search_placeholder()

    def _on_search_var_changed(self, *_: object) -> None:
        if (
            self._suspend_search_callback
            or self._search_placeholder_active
            or not self._state.is_authenticated
        ):
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

    def _load_result_image(self, image_url: str | None, size: int = 50) -> ImageTk.PhotoImage | None:
        """Charge et redimensionne une image depuis une URL pour l'affichage dans les résultats.
        
        Args:
            image_url: URL de l'image à charger
            size: Taille cible de l'image (par défaut 50x50px)
            
        Returns:
            Image redimensionnée ou None en cas d'erreur
        """
        if not image_url:
            return None
        
        # Vérifier le cache
        cache_key = f"{image_url}_{size}"
        if cache_key in self._result_images:
            return self._result_images[cache_key]
        
        try:
            with urlopen(image_url, timeout=5) as response:
                buffer = io.BytesIO(response.read())
            
            image = Image.open(buffer).convert("RGBA")
            image = ImageOps.fit(image, (size, size), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # Mettre en cache
            self._result_images[cache_key] = photo
            return photo
        except Exception:
            return None

    def _update_profile_avatar(self, avatar_size: int | None = None) -> None:
        if not self._profile_label:
            return

        avatar_url = self._state.avatar_url if self._state.is_authenticated else None
        if not avatar_url:
            self._profile_label.configure(image="", text="🙂")
            self._profile_label.image = None
            return

        # Utiliser la taille fournie ou la taille actuelle
        target_size = avatar_size if avatar_size is not None else self._current_avatar_size
        
        # Ne pas recharger si la taille n'a pas changé et que l'image existe déjà
        # (sauf si c'est un appel explicite avec une nouvelle taille)
        if avatar_size is None and self._profile_photo and target_size == self._current_avatar_size:
            return

        try:
            with urlopen(avatar_url, timeout=5) as response:
                buffer = io.BytesIO(response.read())
        except Exception:
            self._profile_label.configure(image="", text="🙂")
            self._profile_label.image = None
            return

        try:
            avatar_diameter = max(target_size - 16, 32)  # Minimum 32px
            upscale_factor = 2
            working_size = avatar_diameter * upscale_factor
            image = Image.open(buffer).convert("RGBA")
            image = ImageOps.fit(image, (working_size, working_size), Image.LANCZOS)
            mask = Image.new("L", (working_size, working_size), 0)
            drawer = ImageDraw.Draw(mask)
            drawer.ellipse((0, 0, working_size, working_size), fill=255)
            image.putalpha(mask)
            image = image.resize((avatar_diameter, avatar_diameter), Image.LANCZOS)
            self._profile_photo = ImageTk.PhotoImage(image)
            self._current_avatar_size = target_size
        except Exception:
            self._profile_photo = None

        if self._profile_photo:
            self._profile_label.configure(image=self._profile_photo, text="", bg=BACKGROUND_COLOR)
            self._profile_label.image = self._profile_photo
        else:
            self._profile_label.configure(image="", text="🙂", bg=BACKGROUND_COLOR)
            self._profile_label.image = None

    # --------------------------------------------------------------- Callbacks -
    def _try_auto_authenticate(self) -> None:
        """Tente une authentification automatique depuis le cache au démarrage."""
        try:
            user = self._service.try_authenticate_from_cache()
            if user:
                # Authentification réussie depuis le cache
                self._state.username = user.get("display_name") or user.get("id")
                images = user.get("images") or []
                self._state.avatar_url = images[0].get("url") if images else None
                self._update_auth_ui()
                self.refresh_devices()
                # Démarrer la surveillance de la lecture pour détecter ce qui est joué
                self._start_progress_update()
        except Exception:
            # En cas d'erreur, ne rien faire - l'utilisateur devra se connecter manuellement
            pass

    def authenticate_spotify(self) -> None:
        try:
            user = self._service.authenticate()
        except ConfigError as exc:
            messagebox.showwarning("Identifiants manquants", str(exc))
            return
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur d'authentification",
                f"Impossible de se connecter à Spotify : {exc}",
            )
            return

        self._state.username = user.get("display_name") or user.get("id")
        images = user.get("images") or []
        self._state.avatar_url = images[0].get("url") if images else None
        self._update_auth_ui()

        self.refresh_devices()
        # Démarrer la surveillance de la lecture pour détecter ce qui est joué
        self._start_progress_update()

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
            self._auth_button.configure(state=tk.DISABLED)
            self._auth_button.grid_remove()
            self._search_entry.configure(state=tk.NORMAL)
            self._search_entry.focus()
            self._refresh_devices_button.configure(state=tk.NORMAL)
            self._update_device_icon()
        else:
            self._auth_button.configure(
                text="Connexion",
                command=self.authenticate_spotify,
                state=tk.NORMAL,
            )
            self._auth_button.grid()
            if self._search_after_id:
                try:
                    self.root.after_cancel(self._search_after_id)
                except ValueError:
                    pass
                self._search_after_id = None
            self._search_entry.configure(state=tk.DISABLED)
            self._set_search_placeholder()
            self._refresh_devices_button.configure(state=tk.DISABLED)
            self._clear_results_display()
            self._state.clear_tracks()
            self._device_var.set("")
            if self._device_menu:
                self._device_menu.delete(0, "end")
            self._update_device_icon()
            # Désactiver les contrôles de lecture
            if self._play_pause_button:
                self._play_pause_button.configure(state=tk.DISABLED)
            if self._previous_button:
                self._previous_button.configure(state=tk.DISABLED)
            if self._next_button:
                self._next_button.configure(state=tk.DISABLED)
            self._stop_progress_update()
            # Réinitialiser l'affichage du titre actuel
            self._update_current_track_display(None)
        self._update_profile_avatar()

    def search_tracks(self, manual_trigger: bool = False) -> None:
        if manual_trigger and self._search_after_id:
            try:
                self.root.after_cancel(self._search_after_id)
            except ValueError:
                pass
        self._search_after_id = None

        if self._search_placeholder_active:
            if manual_trigger:
                messagebox.showwarning(
                    "Recherche vide",
                    "Veuillez saisir un titre, un artiste, un album ou une playlist.",
                )
            else:
                self._clear_results_display()
                self._state.clear_tracks()
            return

        query = self._search_entry.get()

        if not query.strip():
            if manual_trigger:
                messagebox.showwarning(
                    "Recherche vide",
                    "Veuillez saisir un titre, un artiste, un album ou une playlist.",
                )
            else:
                self._clear_results_display()
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

        # Nettoyer les résultats précédents
        self._clear_results_display()
        self._state.clear_tracks()

        if not tracks:
            if manual_trigger:
                messagebox.showinfo(
                    "Aucun résultat",
                    "Aucun résultat trouvé pour cette recherche.",
                )
            return

        entries: list[tuple[str, str, str, str | None]] = []
        for result in tracks:
            if not isinstance(result, dict):
                continue
                
            result_type = result.get("result_type", "track")
            uri = result.get("uri", "")
            
            # Extraire l'URL de l'image selon le type
            image_url: str | None = None
            try:
                if result_type == "track":
                    # Pour les tracks, l'image est dans album.images
                    album = result.get("album", {})
                    if isinstance(album, dict):
                        images = album.get("images", [])
                        if images and isinstance(images, list) and len(images) > 0:
                            image_url = images[0].get("url") if isinstance(images[0], dict) else None
                else:
                    # Pour albums, artists, playlists, l'image est directement dans images
                    images = result.get("images", [])
                    if images and isinstance(images, list) and len(images) > 0:
                        image_url = images[0].get("url") if isinstance(images[0], dict) else None
            except (KeyError, IndexError, TypeError):
                image_url = None
            
            # Formater l'affichage selon le type
            try:
                if result_type == "track":
                    title = result.get("name", "Sans titre")
                    artists = result.get("artists", [])
                    artist = artists[0].get("name", "Artiste inconnu") if artists else "Artiste inconnu"
                    display_name = f"{title} – {artist}"
                elif result_type == "album":
                    album_name = result.get("name", "Sans titre")
                    artists = result.get("artists", [])
                    artist = artists[0].get("name", "Artiste inconnu") if artists else "Artiste inconnu"
                    display_name = f"{album_name} – {artist}"
                elif result_type == "artist":
                    artist_name = result.get("name", "Artiste inconnu")
                    display_name = artist_name
                elif result_type == "playlist":
                    playlist_name = result.get("name", "Sans titre")
                    owner_data = result.get("owner", {})
                    owner = owner_data.get("display_name", "Utilisateur inconnu") if isinstance(owner_data, dict) else "Utilisateur inconnu"
                    display_name = f"{playlist_name} – {owner}"
                else:
                    display_name = result.get("name", "Inconnu")
                
                # Ne pas ajouter si l'URI est vide
                if uri:
                    entries.append((display_name, uri, result_type, image_url))
            except (KeyError, IndexError, TypeError):
                # Ignorer les résultats malformés
                continue

        self._state.set_tracks(entries)
        self._display_results(entries)

    def _clear_results_display(self) -> None:
        """Nettoie l'affichage des résultats."""
        if not self._results_scrollable_frame:
            return
        
        # Détruire tous les widgets enfants
        for widget in self._results_scrollable_frame.winfo_children():
            widget.destroy()
        
        self._result_items.clear()
        
        # Mettre à jour la région de scroll
        if self._results_canvas:
            self._results_canvas.configure(scrollregion=self._results_canvas.bbox("all"))

    def _display_results(self, entries: list[tuple[str, str, str, str | None]]) -> None:
        """Affiche les résultats de recherche avec leurs images."""
        if not self._results_scrollable_frame:
            return
        
        self._clear_results_display()
        
        for idx, (display_name, uri, result_type, image_url) in enumerate(entries):
            # Créer un frame pour chaque résultat
            item_frame = tk.Frame(
                self._results_scrollable_frame,
                bg="#F8FAFC",
                cursor="hand2",
            )
            item_frame.grid(row=idx, column=0, sticky="ew", padx=0, pady=2)
            item_frame.columnconfigure(1, weight=1)
            
            # Charger l'image
            photo = self._load_result_image(image_url, size=50)
            
            # Label pour l'image (ou placeholder si pas d'image)
            image_label = tk.Label(
                item_frame,
                bg="#F8FAFC",
                width=50,
                height=50,
            )
            if photo:
                image_label.configure(image=photo)
                image_label.image = photo  # Garder une référence
            else:
                # Placeholder si pas d'image - utiliser un caractère simple
                image_label.configure(text="♪", font=("Helvetica", 20), fg="#9CA3AF")
            image_label.grid(row=0, column=0, padx=(8, 12), pady=4, sticky="nw")
            
            # Label pour le texte
            text_label = tk.Label(
                item_frame,
                text=display_name,
                bg="#F8FAFC",
                fg="#0F172A",
                font=("Helvetica", 11),
                anchor="w",
                justify=tk.LEFT,
            )
            text_label.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)
            
            # Bind les événements de clic sur le frame et ses enfants
            def make_click_handler(name: str) -> object:
                def handler(event: tk.Event) -> None:
                    self._select_result(name)
                return handler
            
            def make_double_click_handler(name: str) -> object:
                def handler(event: tk.Event) -> None:
                    self._select_result(name)
                    self.play_selected_track(name)
                return handler
            
            click_handler = make_click_handler(display_name)
            double_click_handler = make_double_click_handler(display_name)
            
            item_frame.bind("<Button-1>", click_handler)
            item_frame.bind("<Double-Button-1>", double_click_handler)
            image_label.bind("<Button-1>", click_handler)
            image_label.bind("<Double-Button-1>", double_click_handler)
            text_label.bind("<Button-1>", click_handler)
            text_label.bind("<Double-Button-1>", double_click_handler)
            
            # Effet hover (seulement si pas déjà sélectionné)
            def make_hover_handlers(frame: tk.Frame, name: str) -> tuple[object, object]:
                def enter(_: tk.Event) -> None:
                    # Ne pas changer si déjà sélectionné
                    if frame.cget("bg") == ACCENT_COLOR:
                        return
                    frame.configure(bg="#E5E7EB")
                    for child in frame.winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(bg="#E5E7EB")
                
                def leave(_: tk.Event) -> None:
                    # Ne pas changer si sélectionné
                    if frame.cget("bg") == ACCENT_COLOR:
                        return
                    frame.configure(bg="#F8FAFC")
                    for child in frame.winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(bg="#F8FAFC")
                
                return enter, leave
            
            enter_handler, leave_handler = make_hover_handlers(item_frame, display_name)
            item_frame.bind("<Enter>", enter_handler)
            item_frame.bind("<Leave>", leave_handler)
            image_label.bind("<Enter>", enter_handler)
            image_label.bind("<Leave>", leave_handler)
            text_label.bind("<Enter>", enter_handler)
            text_label.bind("<Leave>", leave_handler)
            
            # Bind les événements de scroll sur les nouveaux widgets
            def bind_scroll_events(widget: tk.Widget) -> None:
                """Bind les événements de scroll sur un widget."""
                def on_mousewheel_scroll(event: tk.Event) -> None:
                    if self._results_canvas:
                        # Windows/Linux avec delta
                        if hasattr(event, 'delta'):
                            self._results_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                        # Linux avec numéro d'événement
                        elif hasattr(event, 'num'):
                            if event.num == 4:
                                self._results_canvas.yview_scroll(-1, "units")
                            elif event.num == 5:
                                self._results_canvas.yview_scroll(1, "units")
                
                widget.bind("<MouseWheel>", on_mousewheel_scroll)
                widget.bind("<Button-4>", on_mousewheel_scroll)  # Linux scroll up
                widget.bind("<Button-5>", on_mousewheel_scroll)  # Linux scroll down
            
            # Bind les événements de scroll sur tous les widgets de l'item
            bind_scroll_events(item_frame)
            bind_scroll_events(image_label)
            bind_scroll_events(text_label)
            
            self._result_items.append((display_name, item_frame))
        
        # Mettre à jour la région de scroll
        if self._results_canvas:
            self._results_canvas.configure(scrollregion=self._results_canvas.bbox("all"))

    def _select_result(self, display_name: str) -> None:
        """Sélectionne un résultat visuellement."""
        # Désélectionner tous les autres
        for name, frame in self._result_items:
            if name == display_name:
                # Mettre en surbrillance le résultat sélectionné
                frame.configure(bg=ACCENT_COLOR)
                for child in frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg=ACCENT_COLOR, fg="#FFFFFF")
            else:
                # Réinitialiser les autres
                frame.configure(bg="#F8FAFC")
                for child in frame.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg="#F8FAFC", fg="#0F172A")

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
            icon_image = self._icon_speaker_on
            self._device_status_var.set(f"Appareil actif : {selected_device}")
        else:
            icon_image = self._icon_speaker_off
            self._device_status_var.set("Aucun appareil sélectionné")

        self._device_icon.configure(image=icon_image)

    def play_selected_track(self, display_name: str | None = None) -> None:
        """Lance la lecture de l'élément sélectionné (titre, album, playlist ou artiste)."""
        if not self._service.is_authenticated:
            messagebox.showerror(
                "Non connecté",
                "Connectez-vous à Spotify avant de lancer la lecture.",
            )
            return

        # Si display_name n'est pas fourni, trouver le résultat sélectionné
        if display_name is None:
            # Chercher le résultat avec le fond ACCENT_COLOR (sélectionné)
            selected_name = None
            for name, frame in self._result_items:
                if frame.cget("bg") == ACCENT_COLOR:
                    selected_name = name
                    break
            
            if not selected_name:
                messagebox.showwarning(
                    "Aucune sélection",
                    "Veuillez choisir un élément dans la liste.",
                )
                return
            display_name = selected_name
        uri = self._state.track_uris.get(display_name)
        result_type = self._state.result_types.get(display_name, "track")

        if not uri:
            messagebox.showerror(
                "URI introuvable",
                "Impossible de retrouver l'élément sélectionné.",
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
            # Utiliser context_uri pour albums, playlists et artistes
            # Utiliser uris pour les titres individuels
            if result_type == "track":
                self._service.start_playback(device_id=device_id, uris=[uri])
            else:
                self._service.start_playback(device_id=device_id, context_uri=uri)
            self._is_playing = True
            self._update_play_pause_button()
            self._enable_player_controls()
            self._start_progress_update()
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Lecture impossible",
                "Spotify n'a pas pu lancer la lecture. Assurez-vous que la lecture "
                f"est bien possible sur l'appareil actif.\n\nDétails : {exc}",
            )

    def _toggle_play_pause(self) -> None:
        """Bascule entre lecture et pause, ou lance la lecture de l'élément sélectionné."""
        if not self._service.is_authenticated:
            return

        # Vérifier s'il y a une sélection dans la liste
        selected_name = None
        for name, frame in self._result_items:
            if frame.cget("bg") == ACCENT_COLOR:
                selected_name = name
                break
        
        if selected_name:
            # Si un élément est sélectionné, lancer sa lecture (remplace la lecture en cours si nécessaire)
            self.play_selected_track(selected_name)
            return

        # Sinon, contrôler la lecture en cours (peu importe l'appareil)
        device_id = self._get_current_device_id()
        if not device_id:
            messagebox.showwarning(
                "Aucun appareil actif",
                "Aucune lecture en cours et aucun appareil sélectionné.",
            )
            return

        try:
            if self._is_playing:
                self._service.pause_playback(device_id=device_id)
                self._is_playing = False
            else:
                self._service.resume_playback(device_id=device_id)
                self._is_playing = True
            self._update_play_pause_button()
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur de contrôle",
                f"Impossible de contrôler la lecture : {exc}",
            )

    def _next_track(self) -> None:
        """Passe à la piste suivante."""
        if not self._service.is_authenticated:
            return

        device_id = self._get_current_device_id()
        if not device_id:
            messagebox.showwarning(
                "Aucun appareil actif",
                "Aucune lecture en cours et aucun appareil sélectionné.",
            )
            return

        try:
            self._service.next_track(device_id=device_id)
            self._start_progress_update()
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur",
                f"Impossible de passer à la piste suivante : {exc}",
            )

    def _previous_track(self) -> None:
        """Gère le comportement du bouton précédent selon la position dans la piste."""
        if not self._service.is_authenticated:
            return

        device_id = self._get_current_device_id()
        if not device_id:
            messagebox.showwarning(
                "Aucun appareil actif",
                "Aucune lecture en cours et aucun appareil sélectionné.",
            )
            return

        # Récupérer l'état de lecture actuel
        try:
            playback = self._service.get_current_playback()
        except SpotifyServiceError:
            # Pas de piste en cours, ne rien faire
            return

        # Vérifier qu'il y a une piste en cours
        if not playback or not playback.get("item"):
            # Pas de piste en cours, ne rien faire
            return

        progress_ms = playback.get("progress_ms", 0)
        is_in_first_3_seconds = progress_ms < 3000

        try:
            if is_in_first_3_seconds:
                # Dans les 3 premières secondes : essayer de passer à la piste précédente
                try:
                    self._service.previous_track(device_id=device_id)
                    self._start_progress_update()
                except SpotifyServiceError:
                    # Pas de piste précédente, revenir au début de la piste en cours
                    self._service.seek_to_position(0, device_id=device_id)
                    self._start_progress_update()
            else:
                # Au-delà de 3 secondes : revenir au début de la piste en cours
                self._service.seek_to_position(0, device_id=device_id)
                self._start_progress_update()
        except SpotifyServiceError as exc:
            messagebox.showerror(
                "Erreur",
                f"Impossible de contrôler la lecture : {exc}",
            )

    def _get_current_device_id(self) -> str | None:
        """Récupère l'ID de l'appareil actuellement actif.
        
        Essaie d'abord l'appareil actif détecté via l'API Spotify (celui qui joue actuellement),
        puis l'appareil sélectionné dans l'interface (celui où se situe l'application).
        """
        # D'abord, essayer de récupérer l'appareil actif depuis l'API Spotify
        try:
            playback = self._service.get_current_playback()
            if playback:
                device = playback.get("device")
                if device and isinstance(device, dict):
                    device_id = device.get("id")
                    if device_id:
                        return device_id
        except SpotifyServiceError:
            pass
        
        # Si aucun appareil actif détecté, utiliser l'appareil sélectionné dans l'interface
        selected_device_name = self._device_var.get()
        if selected_device_name:
            device_id = self._state.get_device_id(selected_device_name)
            if device_id:
                return device_id
        
        return None

    def _update_play_pause_button(self) -> None:
        """Met à jour l'icône du bouton lecture/pause."""
        if not self._play_pause_button:
            return
        if self._is_playing:
            if self._icon_pause:
                self._play_pause_button.configure(image=self._icon_pause)
                self._play_pause_button.image = self._icon_pause
        else:
            if self._icon_play:
                self._play_pause_button.configure(image=self._icon_play)
                self._play_pause_button.image = self._icon_play

    def _enable_player_controls(self) -> None:
        """Active les boutons de contrôle de lecture."""
        if self._play_pause_button:
            self._play_pause_button.configure(state=tk.NORMAL)
        if self._previous_button:
            self._previous_button.configure(state=tk.NORMAL)
        if self._next_button:
            self._next_button.configure(state=tk.NORMAL)

    def _format_time(self, milliseconds: int) -> str:
        """Formate le temps en millisecondes au format MM:SS."""
        total_seconds = milliseconds // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def _update_progress(self) -> None:
        """Met à jour la barre de progression et les labels de temps."""
        if not self._service.is_authenticated:
            self._stop_progress_update()
            return

        try:
            playback = self._service.get_current_playback()
            if not playback:
                # Pas de lecture en cours
                self._is_playing = False
                self._update_play_pause_button()
                self._update_current_track_display(None)
                # Désactiver les contrôles s'il n'y a pas de lecture
                if self._play_pause_button:
                    self._play_pause_button.configure(state=tk.DISABLED)
                if self._previous_button:
                    self._previous_button.configure(state=tk.DISABLED)
                if self._next_button:
                    self._next_button.configure(state=tk.DISABLED)
                self._progress_update_job = self.root.after(1000, self._update_progress)
                return

            item = playback.get("item")
            is_playing = playback.get("is_playing", False)
            
            # Si une piste est en cours, activer les contrôles
            if item:
                self._is_playing = is_playing
                self._update_play_pause_button()
                self._update_current_track_display(item)
                self._enable_player_controls()
            else:
                # Pas de piste en cours même si playback existe
                self._is_playing = False
                self._update_play_pause_button()
                self._update_current_track_display(None)
                # Désactiver les contrôles
                if self._play_pause_button:
                    self._play_pause_button.configure(state=tk.DISABLED)
                if self._previous_button:
                    self._previous_button.configure(state=tk.DISABLED)
                if self._next_button:
                    self._next_button.configure(state=tk.DISABLED)
                self._progress_update_job = self.root.after(1000, self._update_progress)
                return

            progress_ms = playback.get("progress_ms", 0)
            duration_ms = item.get("duration_ms", 0) if item else 0

            if duration_ms > 0 and self._progress_bar:
                progress_percent = (progress_ms / duration_ms) * 100
                self._progress_bar["value"] = progress_percent

            if self._time_label:
                self._time_label.configure(text=self._format_time(progress_ms))

            if self._remaining_time_label:
                remaining_ms = duration_ms - progress_ms
                remaining_text = f"-{self._format_time(remaining_ms)}"
                self._remaining_time_label.configure(text=remaining_text)

            self._progress_update_job = self.root.after(1000, self._update_progress)
        except SpotifyServiceError:
            # En cas d'erreur, arrêter la mise à jour
            self._stop_progress_update()

    def _start_progress_update(self) -> None:
        """Démarre la mise à jour périodique de la barre de progression."""
        self._stop_progress_update()
        self._update_progress()

    def _stop_progress_update(self) -> None:
        """Arrête la mise à jour périodique de la barre de progression."""
        if self._progress_update_job:
            try:
                self.root.after_cancel(self._progress_update_job)
            except ValueError:
                pass
            self._progress_update_job = None

    def _update_current_track_display(self, item: dict[str, Any] | None) -> None:
        """Met à jour l'affichage du titre actuellement en cours de lecture."""
        if not item:
            # Aucune piste en cours
            if self._current_track_title_label:
                self._current_track_title_label.configure(text="Aucune lecture en cours")
            if self._current_track_artist_label:
                self._current_track_artist_label.configure(text="")
            if self._current_track_image_label:
                self._current_track_image_label.configure(image="", text="♪", font=("Helvetica", 24), fg="#9CA3AF")
                self._current_track_image_label.image = None
            self._current_track_image = None
            return

        # Extraire les informations du morceau
        track_name = item.get("name", "Titre inconnu")
        artists = item.get("artists", [])
        artist_name = artists[0].get("name", "Artiste inconnu") if artists else "Artiste inconnu"
        
        # Extraire l'image de l'album
        album = item.get("album", {})
        images = album.get("images", []) if isinstance(album, dict) else []
        image_url = None
        if images and isinstance(images, list) and len(images) > 0:
            # Prendre la première image disponible (généralement la plus grande)
            image_url = images[0].get("url") if isinstance(images[0], dict) else None

        # Mettre à jour les labels texte
        if self._current_track_title_label:
            self._current_track_title_label.configure(text=track_name)
        if self._current_track_artist_label:
            self._current_track_artist_label.configure(text=artist_name)

        # Charger et afficher l'image
        if self._current_track_image_label:
            if image_url:
                try:
                    photo = self._load_result_image(image_url, size=60)
                    if photo:
                        self._current_track_image_label.configure(image=photo, text="")
                        self._current_track_image_label.image = photo
                        self._current_track_image = photo
                    else:
                        # Si le chargement échoue, afficher le placeholder
                        self._current_track_image_label.configure(image="", text="♪", font=("Helvetica", 24), fg="#9CA3AF")
                        self._current_track_image_label.image = None
                except Exception:
                    # En cas d'erreur, afficher le placeholder
                    self._current_track_image_label.configure(image="", text="♪", font=("Helvetica", 24), fg="#9CA3AF")
                    self._current_track_image_label.image = None
            else:
                # Pas d'image disponible
                self._current_track_image_label.configure(image="", text="♪", font=("Helvetica", 24), fg="#9CA3AF")
                self._current_track_image_label.image = None

    # ----------------------------------------------------------------- Public -
    def run(self) -> None:
        self.root.mainloop()

