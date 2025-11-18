"""Structures de données partagées entre la couche UI et les services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class AppState:
    """État interne de l'application."""

    track_uris: dict[str, str] = field(default_factory=dict)
    device_map: dict[str, str] = field(default_factory=dict)
    username: str | None = None

    def clear_tracks(self) -> None:
        self.track_uris.clear()

    def set_tracks(self, entries: Iterable[tuple[str, str]]) -> None:
        self.track_uris.clear()
        for display_name, uri in entries:
            self.track_uris[display_name] = uri

    def set_devices(self, devices: Iterable[tuple[str, str]]) -> None:
        self.device_map = {name: device_id for name, device_id in devices}

    def get_device_id(self, device_name: str) -> str | None:
        return self.device_map.get(device_name)

