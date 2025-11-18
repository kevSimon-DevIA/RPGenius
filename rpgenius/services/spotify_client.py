"""Encapsulation des appels au SDK Spotify."""

from __future__ import annotations

import os
from typing import Any, Iterable

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from rpgenius.config import ConfigError, SpotifyConfig


class SpotifyServiceError(RuntimeError):
    """Erreur générique levée lors des appels à l'API Spotify."""


class SpotifyService:
    """Service responsable de l'authentification et des appels Spotify."""

    def __init__(self, config: SpotifyConfig, *, cache_path: str = ".spotify_cache") -> None:
        self._config = config
        self._cache_path = cache_path
        self._auth_manager: SpotifyOAuth | None = None
        self._client: spotipy.Spotify | None = None

    @property
    def is_authenticated(self) -> bool:
        return self._client is not None

    def authenticate(self) -> dict[str, Any]:
        """Initialise la session Spotify et retourne l'utilisateur courant."""
        if not self._config.credentials_are_configured():
            raise ConfigError(
                "Les identifiants Spotify ne sont pas configurés. "
                "Définissez SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET."
            )

        try:
            self._auth_manager = SpotifyOAuth(
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
                redirect_uri=self._config.redirect_uri,
                scope=self._config.scope,
                open_browser=True,
                cache_path=self._cache_path,
            )
            self._client = spotipy.Spotify(auth_manager=self._auth_manager)
            return self._client.current_user()
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Erreur Spotify lors de l'authentification.") from exc
        except Exception as exc:  # noqa: BLE001
            raise SpotifyServiceError("Échec de l'authentification Spotify.") from exc

    def logout(self) -> None:
        """Déconnecte l'utilisateur et supprime le cache des identifiants."""
        self._client = None
        self._auth_manager = None

        try:
            os.remove(self._cache_path)
        except FileNotFoundError:
            pass

    def search_tracks(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Retourne une liste de pistes Spotify correspondant à la requête."""
        if not query.strip():
            return []

        client = self._ensure_client()
        try:
            results = client.search(q=query, type="track", limit=limit)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Erreur Spotify lors de la recherche de pistes.") from exc

        return results.get("tracks", {}).get("items", [])

    def list_devices(self) -> list[dict[str, Any]]:
        """Retourne la liste des appareils disponibles."""
        client = self._ensure_client()
        try:
            data = client.devices()
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Erreur Spotify lors de la récupération des appareils.") from exc

        return data.get("devices", [])

    def start_playback(self, *, device_id: str, uris: Iterable[str]) -> None:
        """Lance la lecture des pistes fournies sur l'appareil spécifié."""
        client = self._ensure_client()
        uri_list = list(uris)
        if not uri_list:
            raise SpotifyServiceError("Aucune piste fournie pour la lecture.")

        try:
            client.start_playback(device_id=device_id, uris=uri_list)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu lancer la lecture.") from exc

    def _ensure_client(self) -> spotipy.Spotify:
        if self._client is None:
            raise SpotifyServiceError("Aucune session Spotify active. Authentifiez-vous d'abord.")
        return self._client

