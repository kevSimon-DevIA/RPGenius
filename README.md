## RPGenius

Prototype d’application de bureau pour piloter Spotify depuis une interface Tkinter.

### Prérequis

- Python 3.12 (ou compatible)
- [uv](https://docs.astral.sh/uv/) installé
- Identifiants Spotify : `Client ID`, `Client Secret`, `Redirect URI`

### Installation

```bash
uv sync
```

### Configuration

Renseignez vos identifiants dans un fichier `.env` à la racine :

```env
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
# Optionnel : SPOTIFY_SCOPE=user-modify-playback-state user-read-playback-state
```

Ils seront chargés automatiquement lors du démarrage ; aucun `export` n’est requis.

### Structure du projet

- `main.py` : point d’entrée qui instancie la configuration, le service Spotify et la fenêtre principale.
- `rpgenius/config.py` : lecture/validation de la configuration Spotify.
- `rpgenius/services/spotify_client.py` : encapsulation du SDK Spotipy.
- `rpgenius/state.py` : état partagé (pistes, appareils, utilisateur).
- `rpgenius/ui/app.py` : interface Tkinter et callbacks.

### Lancement

```bash
uv run python main.py
```

La première connexion ouvrira votre navigateur pour autoriser l’application.
