# Albert Code 🇫🇷

<p align="center">
  <img src="media/20260502_195508.png" alt="Albert Code en cours d'utilisation dans le terminal" width="393" />
</p>

**Assistant IA de programmation en ligne de commande, propulsé par l'API Albert.**

> ⚠️ **Projet non officiel et expérimental.** Ce projet n'est affilié ni à la DINUM ni à Mistral AI. Il s'agit d'un fork personnel de [Mistral Vibe](https://github.com/mistralai/mistral-vibe), adapté pour fonctionner avec l'[API Albert](https://albert.api.etalab.gouv.fr). Aucune garantie de stabilité ni de support.

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

Sous Windows, utiliser `albert-code.bat` à la place de `albert-code.sh`.

> [!WARNING]
> **Sous Windows, Albert Code nécessite Windows Terminal pour afficher son interface.** L'invite de commande classique (`cmd.exe`) et la fenêtre PowerShell ouverte directement depuis le menu Démarrer ne savent pas afficher la TUI Textual ; l'application semble alors figée.
>
> ### Installation de Windows Terminal
>
> Windows Terminal est l'application de terminal moderne de Microsoft, gratuite. Sur Windows 11, elle est installée par défaut. Sur Windows 10, l'installation manuelle est nécessaire :
>
> 1. Ouvrir le **Microsoft Store** depuis le menu Démarrer.
> 2. Rechercher **Windows Terminal**, ou ouvrir directement le lien https://aka.ms/terminal (qui redirige vers la page Store https://apps.microsoft.com/detail/9n0dx20hk701).
> 3. Cliquer sur **Obtenir** ou **Installer**. L'opération prend quelques secondes.
>
> Pour les machines sans Microsoft Store, le `.msixbundle` de la dernière version est téléchargeable depuis la page des releases : https://github.com/microsoft/terminal/releases.
>
> ### Utilisation avec Albert Code
>
> 1. Ouvrir le menu Démarrer et taper **Terminal** (sous Windows, le programme est listé sous ce nom et non "Windows Terminal"). L'icône est noire et porte un chevron. Le lancer.
> 2. Par défaut, Windows Terminal ouvre un onglet **PowerShell** : ce comportement est normal et tout à fait approprié. PowerShell est un shell parfaitement compatible avec Albert Code. Windows Terminal n'est qu'un *conteneur de terminal* ; le shell qu'il héberge importe peu (PowerShell, cmd, WSL, etc. fonctionnent tous).
> 3. Se déplacer jusqu'au dossier d'Albert Code et lancer le `.bat` (le préfixe `.\` est requis sous PowerShell pour exécuter un script du dossier courant) :
>
>    ```powershell
>    cd C:\chemin\vers\albert-code
>    .\albert-code.bat
>    ```
>
> Pour confirmer que la session s'exécute bien dans Windows Terminal, taper la commande suivante : `echo $env:WT_SESSION`. La variable doit afficher un identifiant. Si elle est vide, la session n'est pas dans Windows Terminal.
>
> ### Sans Windows Terminal
>
> Le mode programmatique `albert-code.bat -p "votre prompt"` n'utilise pas la TUI et fonctionne dans n'importe quelle console (cmd.exe, PowerShell standard). Il convient aux usages scriptés mais ne fournit pas l'interface interactive.
>
> ### Menu d'installation
>
> Lancer `.\albert-code.bat` sans argument affiche un menu interactif :
>
> 1. **Lancer Albert Code** : démarre l'application normalement.
> 2. **Installer la commande dans le PATH utilisateur** : ajoute le dossier d'Albert Code au `PATH` afin que `albert-code` soit disponible depuis n'importe quel répertoire.
> 3. **Désinstaller la commande du PATH utilisateur** : retire l'entrée du `PATH` (le dossier et l'application restent en place).
> 4. **Quitter** : ferme le menu sans rien lancer.
>
> Avec des arguments (par exemple `albert-code.bat -p "..."` ou `albert-code.bat --version`), le menu est court-circuité et la commande s'exécute directement.

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

Ce fork s'inspire du projet [AlbertCode](https://github.com/XenocodeRCE/AlbertCode) de **Simon Roux** pour plusieurs idées clés liées à l'API Albert : auto-fallback de modèle sur 429 répétés, jauge RPM, mode plan-first avec checkpoints, snapshots Git automatiques avant édition. Les implémentations dans ce fork sont indépendantes mais doivent beaucoup à ses choix de conception.

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
