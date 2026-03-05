# Albert Code 🇫🇷

**Assistant IA de programmation en ligne de commande, propulsé par l'API Albert.**

Albert Code est un fork de [Mistral Vibe](https://github.com/mistralai/mistral-vibe), adapté pour fonctionner avec les modèles de l'[API Albert](https://albert.api.etalab.gouv.fr) (infrastructure souveraine française).

## Étape 1 — Obtenir ta clé API Albert

Avant tout, il te faut une clé d'accès à Albert API.

1. Aller sur https://albert.sites.beta.gouv.fr/access/
2. Remplir le formulaire
3. Recevoir son accès (délai de quelques heures, 24h max)
4. Se connecter à AlbertAPI Playground : https://albert.playground.etalab.gouv.fr/
5. Créer une clé API
6. Copier ta clé API (elle ressemble à `eyJhbGciOi...`)
7. La garder de côté, on en aura besoin plus tard

> 💡 Si besoin de support pour la clé API → Salon Tchap **Albert API - Support & retours utilisateurs**

## Étape 2 — Installation

### Installation rapide (recommandée)

```bash
curl -sSL https://raw.githubusercontent.com/simonaszilinskas/albert-code/main/scripts/install-albert.sh | bash
```

Le script :
- Installe [uv](https://docs.astral.sh/uv/) si nécessaire
- Installe `albert-code` en tant qu'outil CLI
- Écrit la configuration Albert par défaut
- Te demande ta clé API

### Installation manuelle

```bash
# Avec uv
uv tool install "albert-code @ git+https://github.com/simonaszilinskas/albert-code"

# Ou avec pip
pip install "albert-code @ git+https://github.com/simonaszilinskas/albert-code"
```

Puis configure ta clé API :

```bash
albert-code --api-key TA_CLE_API
```

## Étape 3 — Utilisation

Lance Albert Code depuis la racine de ton projet :

```bash
albert-code
```

C'est tout ! Tu peux maintenant discuter avec l'IA pour explorer, modifier et interagir avec ton code.

### Exemples

```
> Trouve tous les TODO dans le projet
> Refactore la fonction main dans cli/main.py
> Explique-moi comment fonctionne ce module
```

### Raccourcis utiles

- `Ctrl+J` ou `Shift+Enter` : nouvelle ligne
- `@fichier.py` : autocomplétion de fichiers
- `!commande` : exécuter une commande shell directement
- `/help` : aide et commandes disponibles
- `Shift+Tab` : activer/désactiver l'auto-approbation des outils

### Modes agents

```bash
albert-code --agent plan           # Lecture seule, exploration
albert-code --agent accept-edits   # Auto-approuve les éditions de fichiers
albert-code --agent auto-approve   # Auto-approuve tout (à utiliser avec précaution)
```

## Configuration

La configuration se trouve dans `~/.albert-code/config.toml`. La clé API est stockée dans `~/.albert-code/.env`.

### Modèles disponibles

| Alias | Modèle | Usage |
|-------|--------|-------|
| `albert-code` (défaut) | Qwen/Qwen3-Coder-30B-A3B-Instruct | Codage |
| `albert-large` | openai/gpt-oss-120b | Généraliste |

Pour changer de modèle :

```bash
albert-code --model albert-large
```

### Serveurs MCP

Albert Code supporte les serveurs [MCP](https://modelcontextprotocol.io/) pour étendre ses capacités. Voir la [documentation de configuration MCP](docs/acp-setup.md) pour plus de détails.

## Crédits

Basé sur [Mistral Vibe](https://github.com/mistralai/mistral-vibe) (Apache 2.0).

## Licence

Copyright 2025 Mistral AI — Licence Apache 2.0. Voir [LICENSE](LICENSE).
