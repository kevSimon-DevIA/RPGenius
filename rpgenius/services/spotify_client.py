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

    def try_authenticate_from_cache(self) -> dict[str, Any] | None:
        """Tente de s'authentifier silencieusement en utilisant le cache.
        
        Retourne les informations de l'utilisateur si l'authentification réussit,
        None sinon (pas de cache valide ou erreur).
        """
        if not self._config.credentials_are_configured():
            return None

        try:
            auth_manager = SpotifyOAuth(
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
                redirect_uri=self._config.redirect_uri,
                scope=self._config.scope,
                open_browser=False,
                cache_path=self._cache_path,
            )
            
            # Créer le client - SpotifyOAuth utilisera automatiquement le cache si disponible
            client = spotipy.Spotify(auth_manager=auth_manager)
            
            # Essayer de récupérer les informations de l'utilisateur
            # Si le token n'est pas valide, cela lèvera une exception
            user = client.current_user()
            
            # Si on arrive ici, l'authentification a réussi
            self._auth_manager = auth_manager
            self._client = client
            return user
        except (spotipy.exceptions.SpotifyException, Exception):  # noqa: BLE001
            # En cas d'erreur (token invalide, expiré, ou absent), retourner None
            return None

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
        """Retourne une liste de résultats Spotify (titres, albums, artistes, playlists) correspondant à la requête."""
        if not query.strip():
            return []

        client = self._ensure_client()
        all_results: list[dict[str, Any]] = []
        
        # Limite par type pour équilibrer les résultats
        limit_per_type = max(limit // 4, 5)  # Au moins 5 résultats par type
        
        try:
            # Recherche de tous les types musicaux en une seule requête
            results = client.search(q=query, type="track,album,artist,playlist", limit=limit_per_type)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Erreur Spotify lors de la recherche.") from exc

        if not isinstance(results, dict):
            return []
        
        # Ajouter les titres
        tracks_data = results.get("tracks")
        if tracks_data and isinstance(tracks_data, dict):
            items = tracks_data.get("items", [])
            if isinstance(items, list):
                for track in items:
                    if isinstance(track, dict):
                        track_copy = {**track}  # Créer une copie shallow
                        track_copy["result_type"] = "track"
                        all_results.append(track_copy)
        
        # Ajouter les albums
        albums_data = results.get("albums")
        if albums_data and isinstance(albums_data, dict):
            items = albums_data.get("items", [])
            if isinstance(items, list):
                for album in items:
                    if isinstance(album, dict):
                        album_copy = {**album}  # Créer une copie shallow
                        album_copy["result_type"] = "album"
                        all_results.append(album_copy)
        
        # Ajouter les artistes
        artists_data = results.get("artists")
        if artists_data and isinstance(artists_data, dict):
            items = artists_data.get("items", [])
            if isinstance(items, list):
                for artist in items:
                    if isinstance(artist, dict):
                        artist_copy = {**artist}  # Créer une copie shallow
                        artist_copy["result_type"] = "artist"
                        all_results.append(artist_copy)
        
        # Ajouter les playlists
        playlists_data = results.get("playlists")
        if playlists_data and isinstance(playlists_data, dict):
            items = playlists_data.get("items", [])
            if isinstance(items, list):
                for playlist in items:
                    if isinstance(playlist, dict):
                        playlist_copy = {**playlist}  # Créer une copie shallow
                        playlist_copy["result_type"] = "playlist"
                        all_results.append(playlist_copy)
        
        return all_results

    def list_devices(self) -> list[dict[str, Any]]:
        """Retourne la liste des appareils disponibles."""
        client = self._ensure_client()
        try:
            data = client.devices()
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Erreur Spotify lors de la récupération des appareils.") from exc

        return data.get("devices", [])

    def start_playback(
        self,
        *,
        device_id: str,
        uris: Iterable[str] | None = None,
        context_uri: str | None = None,
    ) -> None:
        """Lance la lecture sur l'appareil spécifié.
        
        Args:
            device_id: L'ID de l'appareil sur lequel lancer la lecture
            uris: Liste d'URIs de pistes (pour les titres individuels)
            context_uri: URI de contexte (pour albums, playlists, artistes)
        """
        client = self._ensure_client()
        
        if not uris and not context_uri:
            raise SpotifyServiceError("Aucune URI fournie pour la lecture.")

        try:
            if context_uri:
                # Utiliser context_uri pour albums, playlists, artistes
                client.start_playback(device_id=device_id, context_uri=context_uri)
            else:
                # Utiliser uris pour les pistes individuelles
                uri_list = list(uris) if uris else []
                client.start_playback(device_id=device_id, uris=uri_list)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu lancer la lecture.") from exc

    def pause_playback(self, *, device_id: str | None = None) -> None:
        """Met en pause la lecture sur l'appareil spécifié."""
        client = self._ensure_client()
        try:
            client.pause_playback(device_id=device_id)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu mettre en pause la lecture.") from exc

    def resume_playback(self, *, device_id: str | None = None) -> None:
        """Reprend la lecture sur l'appareil spécifié."""
        client = self._ensure_client()
        try:
            client.start_playback(device_id=device_id)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu reprendre la lecture.") from exc

    def next_track(self, *, device_id: str | None = None) -> None:
        """Passe à la piste suivante."""
        client = self._ensure_client()
        try:
            client.next_track(device_id=device_id)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu passer à la piste suivante.") from exc

    def previous_track(self, *, device_id: str | None = None) -> None:
        """Revient à la piste précédente."""
        client = self._ensure_client()
        try:
            client.previous_track(device_id=device_id)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu revenir à la piste précédente.") from exc

    def get_current_playback(self) -> dict[str, Any] | None:
        """Récupère l'état actuel de la lecture."""
        client = self._ensure_client()
        try:
            return client.current_playback()
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu récupérer l'état de la lecture.") from exc

    def seek_to_position(self, position_ms: int, *, device_id: str | None = None) -> None:
        """Se positionne à un moment précis dans la piste en cours."""
        client = self._ensure_client()
        try:
            client.seek_track(position_ms=position_ms, device_id=device_id)
        except spotipy.exceptions.SpotifyException as exc:
            raise SpotifyServiceError("Spotify n'a pas pu se positionner dans la piste.") from exc

    def _ensure_client(self) -> spotipy.Spotify:
        if self._client is None:
            raise SpotifyServiceError("Aucune session Spotify active. Authentifiez-vous d'abord.")
        return self._client

