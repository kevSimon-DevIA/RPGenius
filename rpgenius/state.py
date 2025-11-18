"""Structures de données partagées entre la couche UI et les services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class AppState:
    """État interne de l'application."""

    track_uris: dict[str, str] = field(default_factory=dict)
    result_types: dict[str, str] = field(default_factory=dict)  # Type de résultat (track, album, artist, playlist)
    image_urls: dict[str, str | None] = field(default_factory=dict)  # URLs d'images pour chaque résultat
    device_map: dict[str, str] = field(default_factory=dict)
    username: str | None = None
    avatar_url: str | None = None

    @property
    def is_authenticated(self) -> bool:
        """Retourne True si l'utilisateur est authentifié."""
        return self.username is not None

    def reset(self) -> None:
        """Réinitialise l'état de l'application."""
        self.username = None
        self.avatar_url = None
        self.device_map.clear()
        self.clear_tracks()

    def clear_tracks(self) -> None:
        self.track_uris.clear()
        self.result_types.clear()
        self.image_urls.clear()

    def set_tracks(self, entries: Iterable[tuple[str, str, str, str | None]]) -> None:
        """Définit les pistes avec leur URI, leur type et leur URL d'image.
        
        Args:
            entries: Liste de tuples (display_name, uri, result_type, image_url)
        """
        self.track_uris.clear()
        self.result_types.clear()
        self.image_urls.clear()
        for display_name, uri, result_type, image_url in entries:
            self.track_uris[display_name] = uri
            self.result_types[display_name] = result_type
            self.image_urls[display_name] = image_url

    def set_devices(self, devices: Iterable[tuple[str, str]]) -> None:
        self.device_map = {name: device_id for name, device_id in devices}

    def get_device_id(self, device_name: str) -> str | None:
        return self.device_map.get(device_name)

