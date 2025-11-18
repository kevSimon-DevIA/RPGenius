"""Point d'entrée de l'application RPGenius."""

from __future__ import annotations

from rpgenius.config import load_config
from rpgenius.services import SpotifyService
from rpgenius.state import AppState
from rpgenius.ui.app import MainWindow


def main() -> None:
    """Initialise les dépendances puis lance l'interface Tkinter."""
    config = load_config()
    service = SpotifyService(config)
    state = AppState()
    app = MainWindow(service=service, state=state)
    app.run()


if __name__ == "__main__":
    main()

