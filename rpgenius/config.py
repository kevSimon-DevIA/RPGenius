"""Gestion centralisée de la configuration Spotify."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_SCOPE = "user-modify-playback-state user-read-playback-state"
_PLACEHOLDER_PREFIX = "VOTRE_"


class ConfigError(RuntimeError):
    """Erreur levée lorsque la configuration est invalide."""


@dataclass(frozen=True, slots=True)
class SpotifyConfig:
    """Paramètres nécessaires pour interagir avec l'API Spotify."""

    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = DEFAULT_SCOPE

    def credentials_are_configured(self) -> bool:
        """Indique si les identifiants ont été correctement renseignés."""
        return all(
            value and not value.startswith(_PLACEHOLDER_PREFIX)
            for value in (self.client_id, self.client_secret)
        )


def load_config() -> SpotifyConfig:
    """Charge la configuration Spotify depuis l'environnement."""
    load_dotenv()

    client_id = os.getenv("SPOTIFY_CLIENT_ID", "VOTRE_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "VOTRE_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    scope = os.getenv("SPOTIFY_SCOPE", DEFAULT_SCOPE)

    return SpotifyConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
    )

