# Contribuer à Albert Code

Merci de l'intérêt que vous portez à Albert Code. Votre enthousiasme et votre soutien sont appréciés.

## Statut actuel

**Albert Code est en développement actif.** Le rythme d'itération est soutenu et de nombreux changements ont lieu en coulisses. À cause de ce rythme, la revue des PR et des tickets peut prendre plus de temps que d'habitude.

**Sont particulièrement encouragés :**

- **Les rapports de bug** - aider à identifier et à corriger les problèmes.
- **Les retours et idées** - dire ce qui fonctionne, ce qui ne fonctionne pas, et ce qui pourrait être amélioré.
- **Les améliorations de documentation** - suggérer des clarifications ou signaler ce qui manque.

## Comment faire un retour

### Rapports de bug

En cas de bug, ouvrir un ticket en fournissant les éléments suivants :

1. **Description :** description claire du bug.
2. **Étapes pour reproduire :** procédure détaillée pour reproduire le problème.
3. **Comportement attendu :** ce qui aurait dû se produire.
4. **Comportement réel :** ce qui s'est effectivement produit.
5. **Environnement :**
   - version de Python ;
   - système d'exploitation ;
   - version d'Albert Code.
6. **Messages d'erreur :** messages ou traces d'erreur observés.
7. **Configuration :** extraits pertinents du `config.toml` (en masquant toute information sensible).

### Demandes de fonctionnalité et retours

Les idées sont les bienvenues. Quand vous soumettez un retour ou une discussion sur une nouvelle fonctionnalité :

1. **Éviter les doublons :** consulter les discussions existantes avant d'en créer une nouvelle.
2. **Description claire :** expliquer ce que vous souhaitez voir ou améliorer.
3. **Cas d'usage :** décrire votre cas d'usage et l'intérêt que cela présenterait.
4. **Alternatives :** mentionner les solutions de remplacement éventuellement envisagées.

## Mise en place du développement

Cette section s'adresse aux développeurs qui souhaitent installer le dépôt en local, même si nous n'acceptons pas encore les contributions de code.

### Prérequis

- Python 3.12 ou supérieur.
- Un `python3` fonctionnel avec `venv` et `pip` (`uv` n'est pas nécessaire).

### Installation

1. Cloner le dépôt :

   ```bash
   git clone <url-du-depot>
   cd albert-code
   ```

2. Créer un environnement virtuel et installer les dépendances :

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install pre-commit pytest pytest-asyncio pytest-timeout pytest-xdist respx ruff pyright typos vulture
   ```

   La première commande installe les dépendances d'exécution déclarées dans `pyproject.toml`. La seconde installe les outils de développement utilisés pour les tests, le lint et le typage.

3. (Optionnel) Installer les hooks pre-commit :

   ```bash
   pre-commit install
   ```

   Les hooks pre-commit lanceront automatiquement les vérifications avant chaque commit.

### Configuration des journaux

Les logs sont écrits par défaut dans `~/.albert-code/logs/`. Le comportement de journalisation se contrôle via des variables d'environnement :

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `LOG_LEVEL` | Niveau de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `WARNING` |
| `LOG_MAX_BYTES` | Taille maximale du fichier de log avant rotation | `10485760` (10 Mo) |
| `DEBUG_MODE` | Si `true`, force le niveau `DEBUG` | - |

Exemple :

```bash
LOG_LEVEL=DEBUG albert-code
```

### Lancer les tests

Lancer la totalité des tests :

```bash
pytest
```

Lancer les tests en mode verbeux :

```bash
pytest -v
```

Lancer un fichier de test précis :

```bash
pytest tests/test_agent_tool_call.py
```

### Lint et typage

#### Ruff (lint et formatage)

Vérifier les erreurs de lint sans correction :

```bash
ruff check .
```

Corriger automatiquement les erreurs de lint :

```bash
ruff check --fix .
```

Formater le code :

```bash
ruff format .
```

Vérifier le formatage sans modifier les fichiers (utile en CI) :

```bash
ruff format --check .
```

#### Pyright (typage)

Lancer la vérification de typage :

```bash
pyright
```

#### Hooks pre-commit

Lancer manuellement tous les hooks pre-commit :

```bash
pre-commit run --all-files
```

Les hooks pre-commit comprennent :

- Ruff (lint et formatage) ;
- Pyright (typage) ;
- Typos (orthographe) ;
- validation YAML / TOML ;
- Action-validator (workflows GitHub Actions).

### Style de code

- **Longueur de ligne :** 88 caractères (compatible Black).
- **Annotations de type :** obligatoires pour toutes les fonctions et méthodes.
- **Docstrings :** style Google.
- **Formatage :** Ruff assure le lint et le formatage.
- **Typage :** Pyright (configuré dans `pyproject.toml`).

Voir `pyproject.toml` pour la configuration détaillée de Ruff et Pyright.

## Contributions de code

Les contributions de code ne sont pas acceptées pour le moment, mais elles le seront peut-être à l'avenir. Le cas échéant, ce document sera mis à jour avec :

- la procédure de pull request ;
- les règles de contribution ;
- la procédure de revue.

## Des questions ?

Pour les questions sur l'utilisation d'Albert Code, consulter d'abord le [README](README.md). Pour le reste, ouvrir une discussion ou un ticket.

Merci de contribuer à l'amélioration d'Albert Code.
