"""Structures de données partagées entre la couche UI et les services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class AppState:
    """État interne de l'application."""

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

