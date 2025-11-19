"""Encapsulation des appels au SDK Spotify."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from typing import Any, Iterable
from urllib.parse import urlparse

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.util import get_host_port

from rpgenius.config import ConfigError, SpotifyConfig


def _open_url_with_system_browser(url: str) -> None:
    """Ouvre une URL avec l’outil système adapté à l’environnement."""
    if "WSL_DISTRO_NAME" in os.environ:
        try:
            subprocess.run(["wslview", url], check=False)
            return
        except FileNotFoundError:
            pass

    if sys.platform.startswith("linux"):
        try:
            subprocess.run(["xdg-open", url], check=False)
            return
        except FileNotFoundError:
            pass

    try:
        webbrowser.open(url)
    except webbrowser.Error:
        pass


class SpotifyOAuthWSL(SpotifyOAuth):
    """OAuth personnalisé pour forcer l’ouverture automatique sous Linux/WSL."""

    def _open_auth_url(self) -> None:
        auth_url = self.get_authorize_url()
        _open_url_with_system_browser(auth_url)

    def get_auth_response(self, open_browser=None):
        redirect_info = urlparse(self.redirect_uri)
        redirect_host, redirect_port = get_host_port(redirect_info.netloc)

        if (
            redirect_info.scheme == "http"
            and redirect_host in ("127.0.0.1", "localhost")
            and redirect_port
        ):
            try:
                return self._get_auth_response_local_server(redirect_port)
            except Exception:
                pass

        return super().get_auth_response(open_browser=open_browser)


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
            auth_manager = SpotifyOAuthWSL(
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
            self._auth_manager = SpotifyOAuthWSL(
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

    def _ensure_client(self) -> spotipy.Spotify:
        if self._client is None:
            raise SpotifyServiceError("Aucune session Spotify active. Authentifiez-vous d'abord.")
        return self._client

