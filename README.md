# Albert Code 🇫🇷

<p align="center">
  <img src="media/20260502_195508.png" alt="Albert Code en cours d'utilisation dans le terminal" width="393" />
</p>

**Assistant IA de programmation en ligne de commande, propulsé par l'API Albert.**

> ⚠️ **Projet non officiel et expérimental.** Ce projet n'est affilié ni à la DINUM ni à Mistral AI. Il s'agit d'un fork de [simonaszilinskas/albert-code](https://github.com/simonaszilinskas/albert-code), lui-même fork de [Mistral Vibe](https://github.com/mistralai/mistral-vibe), adapté pour fonctionner avec l'[API Albert](https://albert.api.etalab.gouv.fr). Aucune garantie de stabilité ni de support.

## 1 - Obtention de la clé API Albert

1. Se rendre sur https://albert.sites.beta.gouv.fr/access/ et remplir le formulaire.
2. Attendre la réception de l'accès (quelques heures, 24 h au maximum).
3. Se connecter au Playground : https://albert.playground.etalab.gouv.fr/.
4. Créer une clé API et la copier (elle ressemble à `eyJhbGciOi...`).

> 💡 Pour le support des clés API, rejoindre le salon Tchap **Albert API - Support & retours utilisateurs**.

## 2 - Installation

Pré-requis : Python 3.12 ou supérieur.

```bash
git clone https://github.com/obook/albert-code.git
cd albert-code
./albert-code.sh
```

Le lanceur crée automatiquement un environnement virtuel Python (`.venv/`), installe les dépendances et démarre Albert Code. Au premier lancement, la clé API est demandée.

Sous Windows, utiliser `albert-code.bat` à la place de `albert-code.sh`. Voir [WINDOWS.md](WINDOWS.md) pour les pré-requis (Windows Terminal) et les instructions détaillées.

### Rendre la commande disponible globalement (optionnel)

Pour pouvoir taper `albert-code` depuis n'importe quel dossier au lieu de `/chemin/vers/albert-code/albert-code.sh`, le lanceur propose une sous-commande d'installation qui crée un lien symbolique dans `~/.local/bin/`. Le dossier de travail courant est préservé : Albert Code s'exécute toujours dans le répertoire d'où la commande est appelée.

```bash
./albert-code.sh --install      # installe le lien
./albert-code.sh --uninstall    # retire le lien
```

Si `~/.local/bin` n'est pas dans le `PATH`, le script l'indique et propose la ligne à ajouter au `~/.bashrc` ou `~/.zshrc`.

Pour la procédure équivalente sous Windows (ajout au `PATH` utilisateur), voir [WINDOWS.md](WINDOWS.md).

## 3 - Utilisation

```bash
cd projet/
/chemin/vers/albert-code/albert-code.sh
```

Taper `/help` pour afficher la liste de toutes les commandes disponibles. Quelques commandes spécifiques à Albert méritent d'être signalées :

- `/limits` (alias `/quota`) : affiche les quotas par routeur (rpm, rpd, tpm, tpd) lus depuis `/v1/me/info`.
- `/fallback` : active ou désactive le basculement automatique de modèle après deux 429 consécutifs (par défaut actif, bascule de `albert-code` vers `albert-large` pendant 60 s).
- `/status` : affiche les statistiques de la session (étapes, tokens, coût).

## Documentation complémentaire

Les documents techniques détaillés sont dans le dossier [`docs/`](docs/) :

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - architecture en couches du projet, flux de données, choix de conception.
- [`docs/COMMANDES.md`](docs/COMMANDES.md) - liste exhaustive des commandes, options CLI, raccourcis clavier et outils intégrés.
- [`docs/SECURITE.md`](docs/SECURITE.md) - fiche de sécurité, surface d'attaque, modèle de menaces, conformité RGPD.
- [`docs/ACCESSIBILITE.md`](docs/ACCESSIBILITE.md) - déclaration d'accessibilité (RGAA 4.1).
- [`docs/acp-setup.md`](docs/acp-setup.md) - intégration avec Zed, JetBrains et Neovim via Agent Client Protocol.
- [`docs/proxy-setup.md`](docs/proxy-setup.md) - configuration du proxy HTTP.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) - mise en place de l'environnement de développement.
- [`CHANGELOG.md`](CHANGELOG.md) - journal des modifications par version.

## Remerciements

### Projet amont

Ce dépôt est un fork de [simonaszilinskas/albert-code](https://github.com/simonaszilinskas/albert-code). Merci à ses auteurs et contributeurs :

- [mgesbert](https://github.com/mgesbert)
- [simonaszilinskas](https://github.com/simonaszilinskas)
- [qtrrb](https://github.com/qtrrb)
- [michelTho](https://github.com/michelTho)
- [Nemtecl](https://github.com/Nemtecl)
- [VinceOPS](https://github.com/VinceOPS)

### Inspirations

Ce fork s'inspire également du projet [AlbertCode](https://github.com/XenocodeRCE/AlbertCode) de **Simon Roux** pour plusieurs idées clés liées à l'API Albert :

- **Auto-fallback de modèle sur 429 répétés** : après deux 429 consécutifs sur le modèle principal, bascule automatique vers un modèle de secours pendant 60 s puis retour.
- **Jauge RPM live** : commande slash `/rpm` qui affiche la consommation `requêtes/limite (%) [###···]` du modèle actif sur une fenêtre glissante de 60 s.
- **Debounce global pré-appel** : un délai minimum `60/rpm + 0.05 s` est imposé entre deux appels HTTP, pour éviter les rafales qui déclenchent les 429 (vu dans `_wait_for_slot` côté collègue).
- **Lecture du `Retry-After` dans le corps de réponse** : quand Albert renvoie un message texte du type `"Limit exceeded: 50 requests per minute"`, ce délai est extrait et respecté avant le retry.
- **Table statique des paliers documentés EXP / PROD** par modèle, affichée dans `/limits` à côté du fetch live de `/v1/me/info` : utile pour repérer si le compte est sur le palier expérimental ou production sans appel API supplémentaire.

Les implémentations dans ce fork sont indépendantes mais doivent beaucoup à ses choix de conception.

## Bibliothèques utilisées

| Bibliothèque | Rôle | URL | Licence |
|--------------|------|-----|---------|
| agent-client-protocol | Implémentation Python du protocole ACP | https://github.com/zed-industries/agent-client-protocol | Apache 2.0 |
| anyio | Compatibilité asyncio / trio | https://github.com/agronholm/anyio | MIT |
| cachetools | Caches mémoire avec TTL et LRU | https://github.com/tkem/cachetools | MIT |
| cryptography | Primitives cryptographiques | https://github.com/pyca/cryptography | Apache 2.0 / BSD 3-Clause |
| GitPython | Manipulation de dépôts Git | https://github.com/gitpython-developers/GitPython | BSD 3-Clause |
| giturlparse | Parser d'URL Git | https://github.com/nephila/giturlparse | Apache 2.0 |
| google-auth | Authentification pour les API Google | https://github.com/googleapis/google-auth-library-python | Apache 2.0 |
| httpx | Client HTTP synchrone et asynchrone | https://github.com/encode/httpx | BSD 3-Clause |
| keyring | Accès au gestionnaire de mots de passe du système | https://github.com/jaraco/keyring | MIT |
| markdownify | Conversion HTML vers Markdown | https://github.com/matthewwithanm/python-markdownify | MIT |
| mcp | SDK Python pour Model Context Protocol | https://github.com/modelcontextprotocol/python-sdk | MIT |
| mistralai | SDK Python pour l'API Mistral | https://github.com/mistralai/client-python | Apache 2.0 |
| packaging | Utilitaires de packaging Python | https://github.com/pypa/packaging | Apache 2.0 / BSD 2-Clause |
| pexpect | Contrôle de processus interactifs | https://github.com/pexpect/pexpect | ISC |
| pydantic | Validation de données par annotations de type | https://github.com/pydantic/pydantic | MIT |
| pydantic-settings | Gestion de configuration via Pydantic | https://github.com/pydantic/pydantic-settings | MIT |
| pyperclip | Copier-coller multiplateforme | https://github.com/asweigart/pyperclip | BSD |
| python-dotenv | Chargement de variables depuis `.env` | https://github.com/theskumar/python-dotenv | BSD 3-Clause |
| PyYAML | Parser et serialiseur YAML | https://github.com/yaml/pyyaml | MIT |
| requests | Client HTTP synchrone | https://github.com/psf/requests | Apache 2.0 |
| Rich | Rendu coloré et formaté pour le terminal | https://github.com/Textualize/rich | MIT |
| Textual | Cadre de TUI moderne | https://github.com/Textualize/textual | MIT |
| textual-speedups | Optimisations pour Textual | https://github.com/Textualize/textual-speedups | MIT |
| tomli-w | Écriture de fichiers TOML | https://github.com/hukkin/tomli-w | MIT |
| tree-sitter | Parser incrémental | https://github.com/tree-sitter/tree-sitter | MIT |
| tree-sitter-bash | Grammaire bash pour tree-sitter | https://github.com/tree-sitter/tree-sitter-bash | MIT |
| watchfiles | Surveillance de fichiers basée sur Rust | https://github.com/samuelcolvin/watchfiles | MIT |
| zstandard | Compression Zstandard pour Python | https://github.com/indygreg/python-zstandard | BSD 3-Clause |

## Licence

Basé sur [Mistral Vibe](https://github.com/mistralai/mistral-vibe) - Apache 2.0. Voir [LICENSE](LICENSE).
