# Backend Pilot

Application pilote avec interface Leaflet pour visualiser le parcours d'une voiture autonome en temps réel via Kafka.

## Fonctionnalités

- Interface web avec carte Leaflet
- Connexion Kafka pour recevoir les instructions de navigation
- Marqueur dynamique sur la carte suivant les coordonnées GPS
- Modale de démarrage pour envoyer le checkpoint "ready"
- Envoi automatique de checkpoints à chaque instruction

## Installation

```bash
uv sync
```

## Lancement

```bash
uv run python app.py
```

L'application sera accessible sur http://localhost:8000